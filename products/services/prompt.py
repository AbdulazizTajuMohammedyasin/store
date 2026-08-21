class ReviewPromptBuilder:

    MAX_COMMENT_LENGTH = 500

    @staticmethod
    def _format_comment(review) -> str:
        comment = (review.comment or "").strip()
        if not comment:
            return "No comment provided"
        if len(comment) > ReviewPromptBuilder.MAX_COMMENT_LENGTH:
            comment = comment[: ReviewPromptBuilder.MAX_COMMENT_LENGTH] + "..."
        return comment

    @staticmethod
    def build(reviews) -> str:
        formatted_reviews = "\n".join(
            f'- Rating: {review.rating}/5 | Comment: "{ReviewPromptBuilder._format_comment(review)}"'
            for review in reviews
        )

        return f"""
You are a product review analyst.

Read the customer reviews below and write a short, neutral summary of overall
customer sentiment.

Customer reviews:
{formatted_reviews}

Instructions:
- Write 2-3 sentences summarizing what customers think overall.
- Mention the most common positives and negatives if there are any.
- Do not invent information that is not supported by the reviews.
- Respond with plain text only. No markdown, no JSON, no headers.
""".strip()