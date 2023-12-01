import random


def format_business_context(business: dict):
    context = ""
    if title := business.get('title'):
        context += f"- Business: {title}\n"
    if industry := business.get('industry'):
        context += f"- Industry: {industry}\n"
    if niche := business.get('niche'):
        context += f"- Niche: {niche}\n"
    if tone := business.get('tone'):
        context += f"- Tone: {tone}\n"
    if core_values := business.get('core_values'):
        context += f"- Core values: {core_values}\n"
    if audience := business.get('audience'):
        context += f"- Customers: {audience}\n"
    if pain_points := business.get('pain_points'):
        context += f"- Customers pain points: {pain_points}\n"
    if objectives := business.get('objectives'):
        context += f"- Customers objectives: {objectives}\n"

    return context


def format_facts(business: dict):
    facts = ""
    if testimonials := business.get('testimonials'):
        facts += f"- testimonials: {random.choice(testimonials)}\n"
    if events := business.get('events'):
        facts += f"- events: {random.choice(events)}\n"
    if contact_phone := business.get('contact_phone'):
        facts += f"- contact phone: {contact_phone}\n"
    if contact_email := business.get('contact_email'):
        facts += f"- contact email: {contact_email}\n"
    if website := business.get('website'):
        facts += f"- website: {website}\n"

    return facts


def format_topic(content_topic: dict):
    return f"{content_topic.get('title')} -- {content_topic.get('summary')}" or content_topic.get('body')
