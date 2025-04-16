import json
import re
import time

import requests
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(name: str) -> str:
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'__', '_', name)
    return name.strip('_')


def to_class_name(name: str) -> str:
    cleaned_name = re.sub(r'[^a-zA-Z0-9]', '_', name).strip('_')
    cleaned_name = re.sub(r'__', '_', cleaned_name)
    if re.match(r'^\d', cleaned_name):
        cleaned_name = "s" + cleaned_name
    return ''.join(x for x in cleaned_name.split('_'))


def sanitize_field(name: str) -> str:
    name = re.sub(r'\W', '_', name)
    if re.match(r'^\d', name):
        name = "_" + name
    return name


def create_enum(name: str, values: list) -> str:
    try:
        fields = []
        for v in values:
            enum_field = re.sub(r"[^a-zA-Z0-9]", "_", v).upper()
            if re.match(r"^\d", enum_field):
                enum_field = "_" + enum_field
            fields.append(f'    {enum_field} = "{v}"')

        fields_str = "\n".join(fields)
        return f"""
class {name}(Enum):
{fields_str}

    def __str__(self):
        return self.value
"""
    except:
        fields = "\n".join([f'    s_{v} = "{v}"' for v in values])
        return f"""
class {name}(Enum):
{fields}

    def __str__(self):
        return self.value
"""


def merge_allOf(schema: dict, definitions: dict) -> dict:
    result = {}
    for item in schema.get("allOf", []):
        if "$ref" in item:
            ref_name = item["$ref"].split("/")[-1]
            item = definitions.get(ref_name, {})
        for key, value in item.items():
            if key == "properties":
                result.setdefault("properties", {}).update(value)
            else:
                result[key] = value
    return result


def create_dataclass(name: str, schema: dict, existing_enums: dict, definitions: dict, classes: List[str]) -> str:
    if schema.get("type") == "array" and "items" in schema:
        item = schema["items"]
        item_type = "Any"
        if "$ref" in item:
            item_type = to_class_name(item["$ref"].split("/")[-1])
        elif "type" in item:
            item_type = item["type"]
            if item_type == "string":
                item_type = "str"
            elif item_type in ["integer", "number"]:
                item_type = "int"
            elif item_type == "boolean":
                item_type = "bool"

        return f"""
@dataclass
class {name}:
    items: Optional[List[{item_type}]] = None
"""

    if "allOf" in schema:
        schema = merge_allOf(schema, definitions)

    properties = schema.get("properties", {})
    fields = []

    for prop_name, prop in properties.items():
        sanitized_name = sanitize_field(prop_name)
        prop_type = "Any"
        default_value = f"field(default=None, metadata=config(field_name='{prop_name}'))"

        if "$ref" in prop:
            ref_type = to_class_name(prop["$ref"].split("/")[-1])
            prop_type = ref_type
        elif "type" in prop:
            if "enum" in prop:
                enum_name = to_class_name(name + "_" + prop_name)
                existing_enums[enum_name] = prop["enum"]
                prop_type = enum_name
                default_value = f"{prop_type}"
            elif prop["type"] == "string":
                prop_type = "str"
            elif prop["type"] in ["integer", "number"]:
                prop_type = "int"
            elif prop["type"] == "boolean":
                prop_type = "bool"
            elif prop["type"] == "array":
                items = prop.get("items", {})
                item_type = "Any"

                if "$ref" in items:
                    item_type = to_class_name(items["$ref"].split("/")[-1])
                elif "type" in items:
                    if items["type"] == "object" and "properties" in items:
                        inline_class_name = to_class_name(f"{name}_{prop_name}_Item")
                        classes.append(create_dataclass(inline_class_name, items, existing_enums, definitions, classes))
                        item_type = inline_class_name
                    elif items["type"] == "string":
                        item_type = "str"
                    elif items["type"] in ["integer","number"]:
                        item_type = "int"
                    elif items["type"] == "boolean":
                        item_type = "bool"

                prop_type = f"List[{item_type}]"

        fields.append(f"    {sanitized_name}: Optional[{prop_type}] = {default_value}")

    return f"""
@dataclass
class {name}:
{chr(10).join(fields) if fields else '    pass'}
"""


# The rest of the file remains unchanged (not shown here for brevity)


def generate_service_class(service_name: str, methods: List[str]) -> str:
    return f"""
class {service_name}:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
{''.join(methods)}
"""


def generate_api_client(swagger_json: dict, client_name="APIClient") -> str:
    classes, enums, existing_enums = [], [], {}
    definitions = swagger_json.get("components", {}).get("schemas", {}) or swagger_json.get("definitions", {})

    schema_queue = {to_class_name(name): schema for name, schema in definitions.items()}
    visited = set()

    def resolve_dependencies(class_name):
        if class_name in visited:
            return
        visited.add(class_name)
        schema = schema_queue[class_name]

        if "enum" in schema:
            enums.append(create_enum(class_name, schema["enum"]))

        if "allOf" in schema:
            for item in schema["allOf"]:
                if "$ref" in item:
                    ref_class = to_class_name(item["$ref"].split("/")[-1])
                    resolve_dependencies(ref_class)
        elif "properties" in schema:
            for prop in schema["properties"].values():
                if "$ref" in prop:
                    ref_class = to_class_name(prop["$ref"].split("/")[-1])
                    resolve_dependencies(ref_class)
                elif prop.get("type") == "array":
                    items = prop.get("items", {})
                    if "$ref" in items:
                        ref_class = to_class_name(items["$ref"].split("/")[-1])
                        resolve_dependencies(ref_class)
                    elif items.get("type") == "object":
                        inline_class_name = to_class_name(f"{class_name}_inline")
                        classes.append(create_dataclass(inline_class_name, items, existing_enums, definitions, classes))

        classes.append(create_dataclass(class_name, schema, existing_enums, definitions, classes))

    for cname in list(schema_queue.keys()):
        resolve_dependencies(cname)

    for enum_name, values in existing_enums.items():
        enums.append(create_enum(enum_name, values))

    service_classes = {}
    for path, methods in swagger_json.get("paths", {}).items():
        for method, details in methods.items():
            tags = details.get("tags", ["General"])
            for tag in tags:
                service_name = to_class_name(tag) + "Service"
                if service_name not in service_classes:
                    service_classes[service_name] = []

                func_name = to_snake_case(details.get("", f"{method}_{path.strip('/').replace('/', '_')}"))
                params = details.get("parameters", [])
                path_params = [p["name"] for p in params if p.get("in") == "path"]
                query_params = []
                for p in params:
                    if p.get("in") == "query":
                        query_params.append(p["name"])
                        if "enum" in p.get("schema",""):
                            enums.append(create_enum(to_class_name(p["name"]), p["schema"]["enum"]))
                request_model = None
                response_model = "Any"

                if method in ["post", "put", "patch"]:
                    for param in params:
                        if param.get("in") == "body" and "$ref" in param.get("schema", {}):
                            request_model = to_class_name(param["schema"]["$ref"].split("/")[-1])
                    if "$ref" in details.get("requestBody", {}).get("content", {}).get("application/json", {}).get(
                            "schema", {}):
                        request_model = to_class_name(
                            details["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1])

                responses = ""
                for status_code in details.get("responses", {}):
                    response_schema = details.get("responses", {}).get(status_code, {}).get("content", {}).get(
                        "application/json", {}).get("schema", {})
                    if "$ref" in response_schema:
                        response_model = to_class_name(response_schema["$ref"].split("/")[-1])
                        responses += f"        if response.status_code == {status_code}:\n            return {response_model}(**response.json())\n"

                formatted_path = path
                for p in path_params:
                    print(f"{p}")
                    formatted_path = formatted_path.replace(f"{{{p}}}", f"{{{p.replace('-','_')}}}")

                responses += f"        return response.json()"
                path_params = [path_param.replace("-","_") for path_param in path_params]
                param_list = path_params + [q.replace("-","_") for q in query_params]#[f"{q}:{q}" for q in query_params]
                if request_model:
                    param_list.append(f"data: {request_model}")
                param_string = ", ".join(param_list)


                data_argument = f"data.__dict__ if isinstance(data, {request_model}) else data" if request_model else "None"

                method_code = f"""
    def {func_name}(self, {param_string}) -> Any:
        url = f"{{self.base_url}}{formatted_path}"
        params = {{{', '.join([f'"{p}": {p.replace("-","_")}' for p in query_params])}}}
        headers = self.headers
        response = requests.{method}(url, headers=headers, params=params{', json=' + data_argument if request_model else ''})
{responses}
"""
                service_classes[service_name].append(method_code)

    service_class_code = [generate_service_class(name, methods) for name, methods in service_classes.items()]
    service_instances = "\n".join(
        [f'        self.{to_snake_case(name)} = {name}(self.base_url, self.headers)' for name in service_classes])

    api_client_code = f"""
class {client_name}:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.headers = {{"Content-Type": "application/json", "Authorization": f"Bearer {{api_key}}" if api_key else None}}
{service_instances}
"""

    return "\n".join(enums) + "\n" + "\n".join(classes) + "\n" + "\n".join(service_class_code) + api_client_code


def load_swagger(swagger_url):
    response = requests.get(swagger_url,verify=False)
    return response.json()


if __name__ == "__main__":
    swagger_data = load_swagger("url")
    # with open("<json_file_path>") as f:
    #     swagger_data = json.load(f)

    generated_code = generate_api_client(swagger_data)

    with open("generated_api.py", "w") as f:
        f.write("""import json
import re
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dataclasses_json import config
from enum import Enum\n""" + "\n" + generated_code)

    print("API client code generated in generated_api.py")
