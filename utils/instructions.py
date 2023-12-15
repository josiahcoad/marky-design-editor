def fill_section_instructions(section_name: str):
    if section_name == 'title':
        return "{post-template goes here}"
    elif section_name == 'cta':
        return "{cta}"
    elif section_name == 'business-name':
        return "{business name}"
    elif section_name == 'social-handle':
        return "{social handle or business slug}"
    else:
        return "{post-template continues here}"
