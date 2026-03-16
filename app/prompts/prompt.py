from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_PROMPT_DIR = Path(__file__).parent

env = Environment(
    loader=FileSystemLoader(_PROMPT_DIR),
    autoescape=select_autoescape(["jinja2"]),
)


def render_prompt(template_name: str, **kwargs) -> str:
    template = env.get_template(template_name)
    return template.render(**kwargs)
