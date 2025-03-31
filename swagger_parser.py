import json
import re
import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(name: str) -> str:
    """Convert a given name to snake_case."""
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    return name.strip('_')


def to_class_name(name: str) -> str:
    cleaned_name = re.sub(r'[^a-zA-Z0-9]', '_', name).strip('_')
    return to_camel_case(cleaned_name)


def create_enum(name: str, values: list) -> str:
    fields = "\n".join([f'    {re.sub(r"[^a-zA-Z0-9]", "_", v).upper()} = "{v}"' for v in values])
    return f"""
class {name}(Enum):
{fields}
    
    def __str__(self):
        return self.value  # Returns the string value when the enum is referenced
    """


def create_dataclass(name: str, properties: dict, existing_enums: dict) -> str:
    fields = []
    for prop_name, prop in properties.items():
        prop_type = "Any"
        default_value = "None"

        if "$ref" in prop:
            ref_type = to_class_name(prop["$ref"].split("/")[-1])
            prop_type = ref_type
        elif "type" in prop:
            if "enum" in prop:
                enum_name = to_class_name(name + "_" + prop_name)
                existing_enums[enum_name] = prop["enum"]
                prop_type = enum_name
                default_value = f"{prop_type}.{to_class_name(prop['enum'][0]).upper()}"
            elif prop["type"] == "string":
                prop_type = "str"
            elif prop["type"] == "integer":
                prop_type = "int"
            elif prop["type"] == "boolean":
                prop_type = "bool"
            elif prop["type"] == "array":
                item_type = "Any"
                if "items" in prop:
                    if "$ref" in prop["items"]:
                        item_type = to_class_name(prop["items"]["$ref"].split("/")[-1])
                    elif "type" in prop["items"]:
                        item_type = prop["items"]["type"].capitalize()
                prop_type = item_type.lower()
                if prop_type == "string":
                    prop_type = "str"
                elif prop_type == "integer":
                    prop_type = "int"
                elif prop_type == "boolean":
                    prop_type = "bool"
                elif prop_type == "array":
                    prop_type = f"List[{prop_type}]"

        fields.append(f"    {prop_name}: Optional[{prop_type}] = {default_value}")

    return f"""
@dataclass
class {name}:
{chr(10).join(fields) if fields else '    pass'}
    """


def sort_definitions_by_dependencies(definitions: dict) -> List[str]:
    """Sort definitions to ensure referenced classes are created first."""
    dependencies = {name: set() for name in definitions}

    for name, schema in definitions.items():
        if "properties" in schema:
            for prop in schema["properties"].values():
                if "$ref" in prop:
                    ref_name = prop["$ref"].split("/")[-1]
                    dependencies[name].add(ref_name)

    sorted_classes = []
    while dependencies:
        independent = [name for name, deps in dependencies.items() if not deps]
        if not independent:
            break

        sorted_classes.extend(independent)
        for name in independent:
            del dependencies[name]
        for deps in dependencies.values():
            deps.difference_update(independent)

    return sorted_classes


def generate_api_client(swagger_json: dict, class_name="APIClient") -> str:
    classes = []
    enums = []
    existing_enums = {}
    definitions = swagger_json.get("definitions", {})

    sorted_definitions = sort_definitions_by_dependencies(definitions)

    for def_name in sorted_definitions:
        schema = definitions[def_name]
        if "enum" in schema:
            enums.append(create_enum(to_class_name(def_name), schema["enum"]))
        if "properties" in schema:
            classes.append(create_dataclass(to_class_name(def_name), schema["properties"], existing_enums))

    for enum_name, values in existing_enums.items():
        enums.append(create_enum(enum_name, values))

    service_classes = {}
    for path, methods in swagger_json.get("paths", {}).items():
        service_name = to_class_name(path.strip('/').split('/')[0]) + "Service"
        if service_name not in service_classes:
            service_classes[service_name] = []

        for method, details in methods.items():
            func_name = details.get("operationId", f"{method}_{path.strip('/').replace('/', '_')}").replace("-", "_")
            func_name = to_snake_case(func_name)  # Convert to snake_case

            params = details.get("parameters", [])

            path_params = [p["name"] for p in params if p.get("in") == "path"]
            query_params = [p["name"] for p in params if p.get("in") == "query"]
            request_model = None
            response_model = "Any"

            if method in ["post", "put", "patch"]:
                for param in params:
                    if param.get("in") == "body" and "$ref" in param.get("schema", {}):
                        request_model = to_class_name(param["schema"]["$ref"].split("/")[-1])

            response_schema = details.get("responses", {}).get("200", {}).get("schema", {})
            if "$ref" in response_schema:
                response_model = to_class_name(response_schema["$ref"].split("/")[-1])

            param_list = path_params + query_params
            if request_model:
                param_list.append(f"data: {request_model}")
            param_string = ", ".join(param_list) if param_list else ""

            param_dict_string = ", ".join([f'"{p}": {p}' for p in query_params])
            params_code = f"params = {{{param_dict_string}}} if {query_params} else None"

            formatted_path = path
            for p in path_params:
                formatted_path = formatted_path.replace(f"{{{p}}}", f"{{{p}}}")

            data_argument = f"data.__dict__ if isinstance(data, {request_model}) else data" if request_model else "None"

            method_code = f"""
    def {func_name}(self, {param_string}) -> {response_model}:
        url = f"{{self.base_url}}{formatted_path}"
        {params_code}
        headers = self.headers

        response = requests.{method}(url, headers=headers, params=params{', json=' + data_argument if data_argument else ''})
        return response.json() if response.status_code == 200 else response.json()
            """
            service_classes[service_name].append(method_code)

    service_class_code = []
    for service_name, methods in service_classes.items():
        service_code = f"""
class {service_name}:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
    {''.join(methods)}
        """
        service_class_code.append(service_code)

    service_instances = "\n".join(
        [f'        self.{name.lower()} = {name}(self.base_url, self.headers)' for name in service_classes])

    api_client_code = f"""
class {class_name}:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.headers = {{"Content-Type": "application/json", "Authorization": f"Bearer {{api_key}}" if api_key else None}}
{service_instances}
    """

    return "\n".join(enums) + "\n" + "\n".join(classes) + "\n" + "\n".join(service_class_code) + api_client_code


def load_swagger(swagger_url):
    response = requests.get(swagger_url)
    return response.json()


if __name__ == "__main__":
    swagger_data = load_swagger("https://petstore.swagger.io/v2/swagger.json")
    # with open("aw.json") as f:
    #     swagger_data = json.load(f)

    generated_code = generate_api_client(swagger_data)

    with open("generated_api.py", "w") as f:
        f.write("""import json
import re
import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum\n""" + "\n" + generated_code)

    print("API client code generated in generated_api.py")
