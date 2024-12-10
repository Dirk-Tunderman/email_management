from openai import OpenAI, OpenAIError
import os, dotenv

dotenv.load_dotenv(dotenv.find_dotenv())


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))



def get_beta_generation(prompt, response_format =None, model="gpt-3.5-turbo", temperature=0.5, max_tokens=1000, user_input = None):
    response = client.beta.chat.completions.parse(
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
    return response.choices[0].message.parsed