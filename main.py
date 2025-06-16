import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from functions.call_function import call_function

def main():
    load_dotenv()

    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    verbose = "--verbose" in sys.argv

    if not args:
        print("AI Code Assistant")
        print('\nUsage: python main.py "your prompt here"')
        print('Example: python main.py "How do I build a calculator app?"')
        sys.exit(1)

    prompt = "".join(args)

    if verbose:
        print(f"User prompt: {prompt}")

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    system_prompt = """
    You are a helpful AI coding agent.

    When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

    - List files and directories
    - Read file contents
    - Execute Python files with optional arguments
    - Write or overwrite files

    All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
    """

    messages = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    generate_content(client, messages, verbose, system_prompt)

def generate_content(client, messages, verbose, system_prompt):

    max_iter = 20
    k = 0

    schema_get_files_info = types.FunctionDeclaration(
        name="get_files_info",
        description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "directory": types.Schema(
                    type=types.Type.STRING,
                    description="The directory to list files from, relative to the working directory. If not provided, lists files in the working directory itself.",
                ),
            },
            required=["directory"],
        ),
    )

    schema_get_file_content = types.FunctionDeclaration(
        name="get_file_content",
        description="Returns the content of a specified file in a working directory.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "file_path": types.Schema(
                    type=types.Type.STRING,
                    description="The path of the file that is to have its content extracted.",
                ),
            },
        ),
    )

    schema_write_file = types.FunctionDeclaration(
        name="write_file",
        description="Writes content in a specified file. If no such file exists, create a new one with the given content.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "file_path": types.Schema(
                    type=types.Type.STRING,
                    description="The path of the file that is to have its content extracted.",
                ),
                "content": types.Schema(
                    type=types.Type.STRING,
                    description="The content being input into the file.",
                )
            },
            required=["file_path", "content"],
        ), 
    )

    scheme_run_python_file = types.FunctionDeclaration(
        name="run_python_file",
        description="Runs another piece of python code.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "file_path": types.Schema(
                    type=types.Type.STRING,
                    description="The path of the file that is to have its content extracted.",
                ),
               "args": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.STRING,
                        description="Optional arguments to pass to the Python file.",
                    ),
                    description="Optional arguments to pass to the Python file.",
                ),
            },
            required=["file_path"],
        ),
    )

    available_functions = types.Tool(
        function_declarations=[
            schema_get_files_info,
            schema_get_file_content,
            schema_write_file,
            scheme_run_python_file
        ]
    )

    while k < 20:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001', 
            contents=messages,
            config=types.GenerateContentConfig(tools = [available_functions], system_instruction=system_prompt),
        )
        
        candidate = response.candidates[0]
        messages.append(candidate.content)

        if verbose:
            print(f"Assistant response: {candidate.content}")

        function_calls_made = False

        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                function_calls_made = True
                function_call = part.function_call

                if hasattr(function_call, 'args') and function_call.args:
                    function_call.args["working_directory"] = "calculator"
                
                if verbose:
                    print(f"Executing function: {function_call.name}")
                
                try:
                    # Execute the function
                    function_result = call_function(function_call, verbose)
                    messages.append(function_result)
                    
                    if verbose:
                        print(f"Function result: {function_result.parts[0].function_response.response}")
                        
                except Exception as e:
                    print(f"Error executing function {function_call.name}: {e}")
                    # Add error to conversation
                    error_content = types.Content(
                        role="tool",
                        parts=[
                            types.Part.from_function_response(
                                name=function_call.name,
                                response={"error": str(e)},
                            )
                        ],
                    )
                    messages.append(error_content)

        if not function_calls_made:
            if response.text:
                print("\n" + "="*50)
                print("AI Assistant Response:")
                print("="*50)
                print(response.text)
                print("="*50)
            break
        
        k += 1

    if k == 20:
        print(response.text)

    # response = client.models.generate_content(
    #     model='gemini-2.0-flash-001', 
    #     contents=messages,
    #     config=types.GenerateContentConfig(tools = [available_functions], system_instruction=system_prompt),
    # )

    # if verbose:
    #     print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
    #     print(f"Response tokens: {response.usage_metadata.candidates_token_count}")
    #     print("="*10)
    #     print(response.candidates)
    # if response.function_calls:
    #     for function_call_part in response.function_calls:
    #         function_call_part.args["working_directory"] = "calculator"
    #         res = call_function(function_call_part, True)
    #         print(f"-> {res.parts[0].function_response.response}")
    # print(response.text)

if __name__ == "__main__":
    main()