"""Original VeriFact reasoning template at f115d36c; no wording/spacing edits.

Source: packages/llm_judge/src/llm_judge/prompts.py, lines 142-161.
The Qwen chat wrapper and JSON serialization are explicit local adaptations.
"""
import inspect
import json

SYSTEM = "You are judging whether text written about a patient is supported by information from the patient's electronic health record."


def prompt_determine_verdict_reasoning(json: str) -> str:
    prompt = f"""
## Task:
Using the provided reference from the patient's electronic health record, determine whether the text is supported, not supported, or not addressed by the reference context.

## Detailed Instructions:
1. Compare the text and reference, which is provided in the "text" and "reference" keys of the input JSON object.
2. You may think about the task before answering.
3. Provide a verdict in the output JSON object under the key "verdict".
    a. Determine whether the text is addressed or not addressed by the reference context.
    b. If the text is not addressed by the reference context, output the verdict "Not Addressed".
    c. If the text is addressed and fully supported by the reference context, output the verdict "Supported".
    d. If the text is addressed and not fully supported by the reference context, output the verdict "Not Supported". This includes cases where the text is only partially supported by the reference context.
    e. The only valid outputs are "Supported", "Not Supported", or "Not Addressed".
    d. When determining a verdict, consider the information in the reference context to be correct and the source of truth.
4. Provide a reason for your verdict in the output JSON object under the key "reason". Try to make your reason concise and to the point. You must provide a reason. Do not leave it blank.
5. Format your response as a JSON object with the keys "verdict" and "reason". Return only JSON.

## Input JSON:
{json}
"""
    return inspect.cleandoc(prompt)


def messages(row):
    payload = json.dumps({'text': row['claim'], 'reference': row['reference']}, ensure_ascii=False, indent=4)
    return [dict(role='system', content=SYSTEM), dict(role='user', content=prompt_determine_verdict_reasoning(payload))]


def prompt_ids(tokenizer, row):
    return tokenizer.apply_chat_template(messages(row), tokenize=True, add_generation_prompt=True,
        enable_thinking=False, reasoning_effort='low')
