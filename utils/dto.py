from enum import Enum
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel


class TextColorType(str, Enum):
    DONT_CHANGE = 'DONT_CHANGE'
    ON_BACKGROUND = 'ON_BACKGROUND'
    ON_ACCENT = 'ON_ACCENT'
    ACCENT = 'ACCENT'


class ComponentType(str, Enum):
    TEXT = 'TEXT'
    IMAGE = 'IMAGE'
    SHAPE = 'SHAPE'


class TextMeta(BaseModel):
    max_characters: int
    all_caps: bool = False
    color_type: str = TextColorType.DONT_CHANGE
    optional: bool = False
    instructions: str = ""


class CanvasComponent(BaseModel):
    type: ComponentType
    name: str

    def is_named(self, name, prefix=False):
        return self.name.startswith(name) if prefix else self.name == name


    @staticmethod
    def combine_sb_db(name, sb_component, db_component):
        db_component['max_characters'] = db_component.get('max_characters', 100)
        if not db_component.get('name'):
            db_component['name'] = name
        if sb_component['type'] == 'text':
            return TextComponent(**db_component) # unpack the text meta
        elif sb_component['type'] == 'image':
            try:
                color_editable = sb_component['url']['file'].get('filename', '').endswith('svg') and sb_component['imageSvgFill']
            except:
                color_editable = False                
            if color_editable:
                return ShapeComponent(name=name)
            return ImageComponent(name=name)
        elif sb_component['type'] == 'rectangle':
            return ShapeComponent(name=name)
        else:
            raise ValueError(f"Unknown switchboard component type {sb_component['type']}")


class TextComponent(CanvasComponent, TextMeta):
    type: Literal[ComponentType.TEXT] = ComponentType.TEXT


class ImageComponent(CanvasComponent):
    type: Literal[ComponentType.IMAGE] = ComponentType.IMAGE

    @property
    def is_logo(self):
        # This is just the agreed upon magic string name for a logo
        return self.is_named('logo')

    @property
    def is_logo_bg(self):
        # This is just the agreed upon magic string name for a logo background
        return self.is_named('logo-bg')

    @property
    def is_background_photo(self):
        # This is just the agreed upon magic string name for the background photo
        return self.is_named('image1')


class ShapeComponent(CanvasComponent):
    type: Literal[ComponentType.SHAPE] = ComponentType.SHAPE

    def is_background_colored(self):
        return (self.is_named('object1')
                or self.is_named('colored-layer-background')
                or self.is_named('bc-', prefix=True))

    def is_accent_colored(self):
        return (self.is_named('colored-layer') or self.is_named('ac-', prefix=True))


Components = List[TextComponent | ImageComponent | ShapeComponent]


class FilledTextComponent(TextComponent):
    content: str
    color: Optional[str]
    font: Optional[str]


class FilledImageComponent(ImageComponent):
    url: str


class FilledShapeComponent(ShapeComponent):
    color: str


FilledComponents = List[FilledTextComponent | FilledImageComponent | FilledShapeComponent]


class BaseDBModel(BaseModel):
    id: str = str(uuid.uuid4())


class Canvas(BaseDBModel):
    name: str
    components: Components
    thumbnail_url: str
    thumbnail_url_2: Optional[str] = None
    theme: Optional[str] = None
    approved: bool = False
    notes: Optional[str] = None

    @property
    def has_background_photo(self):
        return any(x for x in self.components if isinstance(x, ImageComponent) and x.is_background_photo)

    @property
    def has_logo(self):
        return any(x for x in self.components if isinstance(x, ImageComponent) and x.is_logo)

    @property
    def background_colored_layer(self):
        return [x for x in self.components if isinstance(x, ShapeComponent) and x.is_background_colored()]

    @property
    def accent_colored_layer(self):
        return [x for x in self.components if isinstance(x, ShapeComponent) and x.is_accent_colored()]

    @property
    def text_components(self):
        return [x for x in self.components if isinstance(x, TextComponent)]

    @property
    def text_keys(self):
        return [x.name for x in self.text_components]

    @property
    def logo(self):
        return self.get_image_named('logo')

    @property
    def logo_bg(self):
        return self.get_image_named('logo-bg')

    def get_image_named(self, name):
        return next((x for x in self.components if isinstance(x, ImageComponent) if x.is_named(name)), None)
