def fill_section_instructions(text_name: str):
    if text_name == 'title':
        return "{post-template goes here}"
    elif text_name == 'cta':
        return "{cta}"
    elif text_name == 'business-name':
        return "{business name}"
    elif text_name == 'social-handle':
        return "{social handle or business slug}"
    else:
        return "{post-template continues here}"
