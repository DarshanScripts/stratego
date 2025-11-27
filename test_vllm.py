from vllm import LLM, SamplingParams

def main():
    print("Loading model...")
    llm = LLM(
        model="meta-llama/Llama-3.1-8B-Instruct",
        tensor_parallel_size=1,
    )

    params = SamplingParams(max_tokens=50)
    output = llm.generate(
        ["Hello strategist, what is your first command?"],
        params
    )[0]
    
    print("\nModel Output:\n", output.outputs[0].text)

if __name__ == "__main__":
    main()
