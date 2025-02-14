import os
from propmptpal.core import CreateAgent
from google import genai
from google.genai import types

# Confirm environment API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    raise EnvironmentError("GEMINI_API_KEY environment variable not found!")

# Initialize Google client and conversation chat
client = genai.Client(api_key=api_key)
chat = client.chats.create(model="gemini-2.0-flash")
chat.current_chat_calls = 0
client.chat_ids = set([chat.id])


# Google sub-class
class GeminiAgent(CreateAgent):

    def __init__(
        self,
        model="gemini-2.0-flash",
        threshold=0.55,
        **kwargs,  # Pass remaining arguments to the base class
    ):
        # Set default valid models for Gemini
        google_models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]
        # Pricing as of February 8, 2025
        google_rates = {
            "gemini-2.0-flash": (0.1, 0.4),
            "gemini-2.0-flash-lite": (0.075, 0.3),
            "gemini-1.5-flash": (0.075, 0.3),
        }

        # Initialize the base class with all parameters
        super().__init__(model=model, valid_models=google_models, **kwargs)
        self.self.small_model = "gemini-2.0-flash-lite"

        # Gemini-specific attributes
        self.threshold = threshold

        # Agent-specific chat params
        global chat
        self.chat_id = chat.id
        self.chat_history = []
        chat.message_limit = self.message_limit
        if self.new_chat == True:
            self.start_new_chat()

        # Update token counters
        global total_tokens
        if self.model not in total_tokens.keys():
            total_tokens[self.model] = {"prompt": 0, "completion": 0}

        # Generate agent configuration
        self._create_agent_configuration()

    def _init_chat_completion(self, prompt, model):
        """Initialize and submit a single chat completion request"""
        cfg = types.GenerateContentConfig(
            temperature=self.temperature,
            topP=self.top_p,
            seed=self.seed,
            candidateCount=self.iterations,
        )

        prompt = [prompt] if isinstance(prompt, str) else prompt
        completion = client.models.generate_content(
            model=model, contents=prompt, config=cfg
        )
        self._update_token_count(completion)
        self._calculate_cost(google_rates)

        return completion.text

    def start_new_chat(self, context=""):
        """Start a new chat with only the current agent and adds previous context if needed."""
        global chat
        chat = client.chats.create(model=self.model, context=context)
        chat.current_chat_calls = 0
        chat.message_limit = self.message_limit

        global client
        client.chat_ids |= set([chat.id])
        self.chat_id = chat.id
        self._log_and_print(
            f"New chat created and added to current agent: {self.chat_id}\n",
            self.verbose,
            self.logging,
        )

    def _update_token_count(self, response_obj):
        """Updates token count for prompt and completion."""
        usage = response_obj.usage_metadata
        global total_tokens
        total_tokens[self.model]["prompt"] += usage["prompt_token_count"]
        total_tokens[self.model]["completion"] += usage["candidates_token_count"]
        # Agent-specific counts
        self.tokens["prompt"] += usage["prompt_token_count"]
        self.tokens["completion"] += usage["candidates_token_count"]

    def _get_current_messages(self):
        """Fetches all messages from a chat in order and returns them as a text block."""
        conversation = []
        speaker = "User:"
        for entry in self.chat_history:
            conversation.append(f"{speaker}\n{entry}")
            speaker = "System:" if speaker == "User:" else "User:"

        return "\n\n".join(conversation)

    def _send_chat_message(self):
        """Sends a user prompt to an existing chat and retrieves the response."""
        self.chat_history.append({"role": "user", "content": self.prompt})

        # Send user prompt to existing chat and add to the chat history
        response = chat.send_message(self.prompt, config=self.agent)
        self.chat_history.append({"role": "model", "content": response.text})

        return response.text


def _create_agent_configuration(self):
    """Creates a new assistant config based on user-defined parameters."""
    self.agent = types.GenerateContentConfig(
        system_instruction=self.role,
        temperature=self.temperature,
        topP=self.top_p,
        seed=self.seed,
        candidateCount=self.iterations,
        tools=[
            types.Tool(
                google_search=types.GoogleSearchRetrieval(
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        dynamic_threshold=self.threshold
                    )
                )
            )
        ],
    )

    # Requires even more testing
    def _validate_image_params(self, dimensions, quality):
        """Validates image dimensions and quality for the Gemini model."""
        valid_dimensions = {
            "gemini-pro": ["1024x1024", "768x768", "512x512"],  # Example dimensions
            "gemini-ultra": ["2048x2048", "1024x1024", "512x512"],  # Example dimensions
        }

        # Validate dimensions
        if (
            self.model in valid_dimensions
            and dimensions.lower() not in valid_dimensions[self.model]
        ):
            self.dimensions = "1024x1024"  # Default dimension
        else:
            self.dimensions = dimensions

        # Validate quality
        self.quality = (
            "high"
            if quality.lower() in {"h", "hd", "high", "higher", "highest"}
            else "standard"
        )

        # Override quality for specific roles (e.g., photographer)
        if self.label == "photographer":
            self.quality = "high"

        return self.dimensions, self.quality

    # Still needs refactoring
    def _handle_image_request(self):
        """Processes image generation requests using OpenAIs image models."""
        os.makedirs("images", exist_ok=True)

        response = model.generate_image(
            prompt=self.prompt,
            dimensions=self.dimensions,
            quality=self.quality,
        )

        response = client.images.generate(
            model=self.model,
            prompt=self.prompt,
            n=1,
            size=self.dimensions,
            quality=self.quality,
        )
        self._update_token_count(response)
        self._calculate_cost()
        self._log_and_print(
            f"\nRevised initial prompt:\n{response.data[0].revised_prompt}",
            self.verbose,
            self.logging,
        )
        image_data = requests.get(response.data[0].url).content
        image_file = f"images/{self.prefix}.image.png"
        image_file = _check_unique_filename(image_file)
        with open(image_file, "wb") as outFile:
            outFile.write(image_data)

        self.last_message = (
            "\nRevised image prompt:\n"
            + response.data[0].revised_prompt
            + "\nGenerated image saved to:\n"
            + image_file
        )
        self._log_and_print(self.last_message, True, self.logging)
