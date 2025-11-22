import os
from llama_cpp import Llama, LlamaGrammar

class LocalLLMEngine:
    def __init__(self, model_filename="Llama-3.2-1B-Instruct-Q6_K.gguf"):
        self.model_path = os.path.join(os.path.expanduser("~"), ".ai_assistant", "models", model_filename)

        print(f"⚡ Loading AI Model into Memory: {self.model_path}")
        # n_gpu_layers=-1 offloads EVERYTHING to GPU if available.
        # n_ctx=4096 is the context window.
        self.llm = Llama(
            model_path=self.model_path,
            n_gpu_layers=-1,
            n_ctx=4096,
            verbose=False
        )

        # Enhanced GBNF Grammar: Allows either JSON tools OR plain text conversation
        # Solves the "gagged AI" problem by allowing natural responses
        self.tool_grammar = LlamaGrammar.from_string(r'''
            root ::= object | chat

            # Tool Call (JSON) - for actions like opening apps
            object ::= "{" ws "\"tool\"" ":" ws string "," ws "\"parameters\"" ":" ws params "}"

            # Tool Parameters (nested JSON object)
            params ::= "{" ws (string ":" ws value ("," ws string ":" ws value)*)? "}" | "{" ws "}"

            # Conversational Response (Plain text for chat)
            chat ::= [^{}]*

            # Standard JSON building blocks
            string ::= "\"" ([^"\\] | "\\" ["\\/bfnrt] | "\\" "u" [0-9a-fA-F]{4})* "\""
            value ::= object | array | string | number | ("true" | "false") | "null"
            array ::= "[" ws (value ("," ws value)*)? ws "]"
            number ::= ("-"? [0-9]+ ("." [0-9]+)? ([eE] [+-]? [0-9]+)?)
            ws ::= [ \t\n]*
        ''')

    def query(self, user_prompt, system_prompt):
        """
        Direct inference call. 10x faster than HTTP.
        """
        # Construct Llama-3 specific prompt format (without duplicate begin_of_text)
        full_prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

        output = self.llm(
            full_prompt,
            max_tokens=256,
            stop=["<|eot_id|>"],
            grammar=self.tool_grammar,  # <--- UNCOMMENT THIS
            temperature=0.1  # Low temperature for factual tool use
        )

        # The result is GUARANTEED to be JSON due to the grammar
        return output['choices'][0]['text']
