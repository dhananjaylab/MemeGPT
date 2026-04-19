from typing import TypedDict
import json


class MemeData(TypedDict):
    id: int
    name: str
    alternative_names: list[str]
    file_path: str
    font_path: str
    text_color: str
    text_stroke: bool
    usage_instructions: str
    number_of_text_fields: int
    text_coordinates_xy_wh: list[list[int]]    
    example_output: list[str]


def load_meme_data() -> list[MemeData]:
    with open("meme_data.json", "r") as file:
        meme_data: list[dict] = json.load(file)
    return [MemeData(**meme) for meme in meme_data]


def load_meme_data_flat_string() -> str:
    with open("meme_data.json", "r") as file:
        meme_data: str = file.read()
    return meme_data


if __name__ == "__main__":
    meme_data_loaded = load_meme_data()
    first_item = meme_data_loaded[0]
    print(type(first_item))
    print(first_item)
    
    string_data = load_meme_data_flat_string()
    print(type(string_data))