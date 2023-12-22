from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from diffusers import AutoPipelineForText2Image
import textwrap
import argparse
import torch
import os

'''
TODO:
[ ] support for creatures
    [ ] power toughness templates
[ ] support for planeswalkers
[ ] colorless mana
'''

''' Some constants: pre-defined coordinates and sizes used for card-creation 
'''
coord_top_left = (90, 105)
coord_bottom_right = (656,568)
coord_card_name = (83, 50)
coord_card_name_shadow = (coord_card_name[0]+2, coord_card_name[1]+2)
coord_mana_cost_top_right = (687, 50)
coord_card_type = (90, 587)
coord_card_type_shadow = (coord_card_type[0]+2, coord_card_type[1]+2)
coord_rule_text = (100, 666)
coord_footnote_illus = (373, 948)
size_mana_cost = (37, 37)
size_image = (coord_bottom_right[0]-coord_top_left[0], coord_bottom_right[1]-coord_top_left[1])

mtg_font_card_name_small = ImageFont.truetype('fonts/Goudy_Medieval_Alternate.ttf', 37)
mtg_font_card_name_large = ImageFont.truetype('fonts/Goudy_Medieval_Alternate.ttf', 44)
mtg_font_card_type = ImageFont.truetype('fonts/Plantin/Plantin_Roman/Plantin_Roman.ttf', 32)
mtg_font_rules_text = ImageFont.truetype('fonts/Plantin/Plantin_Roman/Plantin_Roman.ttf', 36)
mtg_font_footnote_illus = ImageFont.truetype('fonts/Plantin/Plantin_Roman/Plantin_Roman.ttf', 24)
mtg_font_footnote_gh = ImageFont.truetype('fonts/Plantin/Plantin_Roman/Plantin_Roman.ttf', 14)

text_footnote = 'Illus. StabilityAI SD-Turbo'
text_footnote_model = 'github.com/bmaag90/magic-the-gpt'

def create_illustrations(dict_card, num_images=1, prompt_format='card_name,card_type,rules_text'):
    ''' Creates num_images of card illustrations based on some card information (name, type, rule text)

    Returns:
        arr_images (array of PIL Image): array of generated PIL images
    '''
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float16, variant="fp16")
    pipe.to("cuda")
    prompt = ''
    for s in prompt_format.split(','):
        prompt += '{},'.format(dict_card[s])
    print(prompt)
    arr_images = []
    for n in range(num_images):
        image = pipe(prompt=prompt, num_inference_steps=1, guidance_scale=0.0).images[0]
        arr_images.append(image)

    return arr_images

def get_card_dict_from_test(card_text):
    ''' Processes the raw card string, extracts the relevant fields and returns a dict
    '''
    s = card_text.split(',')

    dict_card = {
        'card_name': s[0].strip(),
        'mana_cost': s[1].strip(),
        'card_type': s[2].strip(),
        'rules_text': ','.join(s[3:-2]).strip(),
        'power': s[-2].strip()[6:],
        'toughness': s[-1].strip()[10:]
    }

    return dict_card

def get_background_image(mana_cost):
    ''' Loads the corresponding card template determined by the manacost
    '''
    list_mana_cost = [x for x in mana_cost if x not in ['{', '}']]

    mc_to_color = {'b': 'black', 'g': 'green', 'r': 'red', 'u': 'blue', 'w': 'white'}
    set_mc_colored = set(['b', 'g', 'r', 'u', 'w'])
    set_list_mana_costs = set(list_mana_cost)

    unique_colored_mana_costs = set_list_mana_costs.intersection(set_mc_colored)

    if len(unique_colored_mana_costs) == 0:
        temp_style = 'colorless'
    elif len(unique_colored_mana_costs) == 1:
        temp_style = mc_to_color[list(unique_colored_mana_costs)[0]]
    else:
        temp_style = 'multicolor'

    template = Image.open('template/{}.png'.format(temp_style))

    return template

def add_illustration(template, illustration):
    ''' Adds the illustration image to the card template
    '''
    illustration_resized = illustration.resize(size_image)

    template.paste(illustration_resized, coord_top_left)

    return template

def add_card_name_text(template, card_name):
    ''' Adds the name of the card to the template
    '''
    card_draw = ImageDraw.Draw(template)

    str_card_name = card_name.strip().title()

    if ('p' in card_name) or ('q' in card_name) or ('g' in card_name):
        mtg_font_card_name = mtg_font_card_name_small
    else:
        mtg_font_card_name = mtg_font_card_name_large
    # add "shadow" effect in black color
    card_draw.text(
        coord_card_name_shadow,
        str_card_name,
        (0,0,0),
        font=mtg_font_card_name
    )
    # add white colored card name
    card_draw.text(
        coord_card_name,
        str_card_name,
        (255,255,255),
        font=mtg_font_card_name
    )

    return template

def add_mana_cost_symbols(template, mana_cost):
    ''' Creates an image of the mana cost and adds it to the card template in the top right corner
    '''
    list_mana_cost = [x for x in mana_cost.strip() if x not in ['{', '}']]
    size_image_mana_cost = (len(list_mana_cost)*size_mana_cost[0], size_mana_cost[1])
    img_mana_cost = Image.new('RGBA', size_image_mana_cost, (0,0,0,0))
    for cnt, mc in enumerate(list_mana_cost):
        template_mana_cost = Image.open('template/ms_{}.png'.format(mc)).convert('RGBA')
        img_mana_cost.paste(template_mana_cost, (0+cnt*size_mana_cost[0], 0))

    coord_mana_cost_adapted = (
        coord_mana_cost_top_right[0] - size_image_mana_cost[0],
        coord_mana_cost_top_right[1]
    )

    template.paste(img_mana_cost, coord_mana_cost_adapted, img_mana_cost)

    return template

def add_card_type_text(template, card_type):
    ''' Adds the card type to the template
    '''
    str_card_type = card_type.strip().title()
    card_draw = ImageDraw.Draw(template)

    card_draw.text(
        coord_card_type_shadow,
        str_card_type,
        (0,0,0),
        font=mtg_font_card_type
    )
    card_draw.text(
        coord_card_type,
        str_card_type,
        (255,255,255),
        font=mtg_font_card_type
    )

    return template

def add_rules_text(template, rules_text):

    str_rule_txt = rules_text.strip()
    card_draw = ImageDraw.Draw(template)

    s = str_rule_txt.split('. ')
    s = [x.capitalize() for x in s]
    str_rule_txt = '. '.join(s)

    wrapper = textwrap.TextWrapper(width=31)   
    multiline_str_rule_text = wrapper.fill(text=str_rule_txt) 
    card_draw.multiline_text(
        coord_rule_text,
        multiline_str_rule_text,
        (0,0,0),
        font=mtg_font_rules_text
    )

    return template

def add_footnote(template):
    ''' Adds some 'footnote' information, i.e. resembles the artist and wotc text
    '''
    card_draw = ImageDraw.Draw(template)

    w, h_i = card_draw.textsize(text_footnote, font=mtg_font_footnote_illus)
    new_coord_footnote_illus = (coord_footnote_illus[0]-int(w/2), coord_footnote_illus[1])
    new_coord_footnote_illus_shadow = (coord_footnote_illus[0]-int(w/2)+2, coord_footnote_illus[1]+2)

    card_draw.text(
        new_coord_footnote_illus_shadow,
        text_footnote,
        (0,0,0),
        font=mtg_font_footnote_illus
    )
    card_draw.text(
        new_coord_footnote_illus,
        text_footnote,
        (255,255,255),
        font=mtg_font_footnote_illus
    )
    
    w, h_g = card_draw.textsize(text_footnote_model, font=mtg_font_footnote_gh)
    new_coord_footnote_gh = (coord_footnote_illus[0]-int(w/2), coord_footnote_illus[1]+h_i+2)

    card_draw.text(
        new_coord_footnote_gh,
        text_footnote_model,
        (0,0,0),
        font=mtg_font_footnote_gh
    )

    return template

def save_image(template, card_name, save_path, idx=0):
    ''' Saves the card as png file 
    '''
    out_name = os.path.join(
        save_path,
        '{}_{}.png'.format(
            '_'.join(card_name.split(' ')),
            idx
        )
    )

    template.save(out_name)

def run(args):
    
    if (len(args.card_string) == 0):
        print('Card text missing')
        return
    
    dict_card = get_card_dict_from_test(args.card_string)

    template = get_background_image(dict_card['mana_cost'])

    template = add_card_name_text(template, dict_card['card_name'])
    template = add_mana_cost_symbols(template, dict_card['mana_cost'])
    template = add_card_type_text(template, dict_card['card_type'])
    template = add_rules_text(template, dict_card['rules_text'])
    template = add_footnote(template)

    arr_illustrations = create_illustrations(dict_card, args.num_examples, args.prompt_format)
    for i in range(args.num_examples):
        template = add_illustration(template, arr_illustrations[i])
        
        save_image(
            template,
            dict_card['card_name'],
            args.save_path,
            idx=i
        )


if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-c', '--card_string', type=str, default='')
    arg_parser.add_argument('-s', '--save_path', type=str, default='examples/')
    arg_parser.add_argument('-n', '--num_examples', type=int, default=3)
    arg_parser.add_argument('-p', '--prompt_format', type=str, default='card_name,card_type,rules_text')
    args = arg_parser.parse_args()

    run(args)
    



    

