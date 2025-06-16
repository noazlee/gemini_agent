from functions.get_files_info import get_files_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.run_python import run_python_file
from google.genai import types


def call_function(function_call_part, verbose=False):
    # types.FunctionCall: .name, .args
    if verbose:
        print(f"Calling function: {function_call_part.name}({function_call_part.args})")
    else:
        print(f" - Calling function: {function_call_part.name}")

    functionMap = {
        "get_file_content": get_file_content,
        "write_file": write_file,
        "run_python_file": run_python_file,
        "get_files_info": get_files_info
    }

    if function_call_part.name not in functionMap:
        return types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=function_call_part.name,
                    response={"error": f"Unknown function: {function_call_part.name}"},
                )
            ],
        )

    function_result = functionMap[function_call_part.name](**function_call_part.args)
    
    return types.Content(
        role="tool",
        parts=[
            types.Part.from_function_response(
                name=function_call_part.name,
                response={"result": function_result},
            )
        ],
    )
