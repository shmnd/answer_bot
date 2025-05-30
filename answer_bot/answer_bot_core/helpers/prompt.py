def build_gpt_prompt(query, context_blocks, opa, opb, opc, opd, correct_answer, explanation):
    return (
        "You are a medical MCQ expert assistant.\n"
        "Given a new MCQ and related historical MCQs (with scores), your task is to:\n"
        "1. Validate the question, options, and explanation.\n"
        "2. Improve the question and options if needed.\n"
        "3. Confirm the correct answer and provide a clearer explanation.\n"
        "4. Return everything in structured JSON.\n\n"
        f"{chr(10).join(context_blocks[:3])}\n\n"
        f"=== NEW MCQ ===\n"
        f"Question: {query}\n"
        f"Option A: {opa}\n"
        f"Option B: {opb}\n"
        f"Option C: {opc}\n"
        f"Option D: {opd}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Explanation: {explanation}\n\n"
        "Please return output as JSON:\n"
        "{\n"
        "  \"improved_question\": \"...\",\n"
        "  \"improved_opa\": \"...\",\n"
        "  \"improved_opb\": \"...\",\n"
        "  \"improved_opc\": \"...\",\n"
        "  \"improved_opd\": \"...\",\n"
        "  \"improved_correct_answer\": \"A/B/C/D\",\n"
        "  \"improved_explanation\": \"...\"\n"
        "}"
    )
