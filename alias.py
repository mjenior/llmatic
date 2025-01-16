#!/usr/bin/env python3

import os
from pathlib import Path


def extract_unique_words(file_path):
    """
    Extract and return a set of unique words from the specified file.
    """
    with open(file_path, "r") as file:
        return {word for line in file for word in line.split()}


if __name__ == "__main__":
    commandStr = '"cli_assistant.py'

    # Determine alias string
    alias = input('Preferred alias string: ')
    alias = alias if alias != '' else 'llm'

    # Prompt refinement
    refine = input('Refine user query (1 = True and 0 = False): ')
    if refine == '1':
        commandStr += f" --refine True"

    # Chain of Thought 
    chain = input('Include Chain-of-Thought reasoning (1 = True and 0 = False): ')
    if chain == '1':
        commandStr += f" --chain_of_thought True"

    # Verbose output
    verbose = input('Verbose output (1 = True and 0 = False): ')
    if verbose == '1':
        commandStr += f" --verbose True"

    # Response reflection
    iters = input('Reflection iteration (integer): ')
    try: 
        iters = int(iters)
        commandStr += f" --iters {int(iters)}"
    except ValueError:
        pass

    # Default role selection
    role = input('Default system role (refer to README): ')
    role = role if role.lower() in ['compbio','cancer','dev','invest','art','rewrite','story'] else ''
    if role != '':
        commandStr += f" --role {role.lower()}"

    # Compose alias text versions
    commandStr += ' --prompt'
    aliasStr = f'alias {alias}="{commandStr}"'
    profileStr = '\n'.join(["\n\n# >>> Added by LLM CLI assistant >>>",
                        f"export PATH=$PATH:{os.path.dirname(os.path.realpath(__file__))}",
                        aliasStr,
                        "# <<< Added by LLM CLI assistant <<<\n\n"])
    aliasWords = set(profileStr.split())

    # Add to current environment
    os.environ.update({alias: commandStr})
    print("\nAlias added to current environment\n")
    
    # Add to bash profiles
    found = 0
    for prfl in ["bashrc", "zshrc", "bash_profile", "bash_aliases"]:
        if os.path.isfile(f"{Path.home()}/.{prfl}"):
            wrds = extract_unique_words(f"{Path.home()}/.{prfl}")
            if len(aliasWords.difference(wrds)) != 0:
                found += 1
                print(f"Updated ~/.{prfl} with command")
                with open(f"{Path.home()}/.{prfl}", "a") as f:
                    f.write(profileStr)

    if found > 0:
        print(f'\nNow you may simply type {alias} followed by your request in quotations to submit queries using your preferred settings.\n')
