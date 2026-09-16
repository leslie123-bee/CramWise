# The one file the AI quiz generator and AI tutor both call into.
#
# Right now AI_API_KEY is not set (you chose to skip that for now), so
# every function here returns a clearly-labelled placeholder instead of
# a real AI answer. Everything else about these features - the
# database, the endpoints, the test page - is fully built and working
# today; only the "ask a real AI" step is stubbed.
#
# When you're ready to turn this on: get an API key from an AI provider
# (e.g. https://console.anthropic.com or https://platform.openai.com),
# put it in your .env as AI_API_KEY=..., and replace the body of
# _call_ai() below with a real HTTP request to that provider. Nothing
# in the controllers or the test page needs to change - they only ever
# call generate_quiz() and tutor_reply().
import os


def is_configured():
    return bool(os.environ.get('AI_API_KEY', '').strip())


def generate_quiz(subject_name, topic, num_questions=5):
    """Returns a list of question dicts:
    [{question, choices: [str, str, str, str], answer_index, explanation}, ...]
    """
    if is_configured():
        # TODO: replace this with a real call to your AI provider, e.g.
        #   response = _call_ai(f"Write {num_questions} multiple-choice
        #   questions about {topic or subject_name} ...")
        #   ... then parse response into the same list-of-dicts shape.
        pass
    return _placeholder_quiz(subject_name, topic, num_questions)


def tutor_reply(subject_name, conversation):
    """conversation: list of {role: 'user'|'assistant', content: str},
    oldest first. Returns the assistant's reply as a plain string."""
    if is_configured():
        # TODO: replace this with a real call to your AI provider, e.g.
        #   response = _call_ai(conversation, system=f"You are a patient
        #   tutor helping a student with {subject_name}.")
        #   return response
        pass
    return _placeholder_tutor_reply(subject_name, conversation)


def _placeholder_quiz(subject_name, topic, num_questions):
    label = topic.strip() if isinstance(topic, str) and topic.strip() else subject_name
    questions = []
    for i in range(1, max(1, num_questions) + 1):
        questions.append({
            'question': f'[Placeholder question {i} on "{label}"] Add an AI_API_KEY in .env to generate real questions here.',
            'choices': ['Option A', 'Option B', 'Option C', 'Option D'],
            'answer_index': 0,
            'explanation': 'This is a placeholder explanation - real ones appear once an AI key is connected.',
        })
    return questions


def _placeholder_tutor_reply(subject_name, conversation):
    last_user_message = ''
    for message in reversed(conversation):
        if message.get('role') == 'user':
            last_user_message = message.get('content', '')
            break
    return (
        f'(AI tutor placeholder - no AI_API_KEY is set yet.) '
        f'You asked about "{last_user_message}" in {subject_name}. '
        f'Once an AI_API_KEY is added to the .env file, this reply will '
        f'come from a real AI instead of this canned message.'
    )
