import json
from urllib import request, parse
import random

# ======================================================================
# This function sends a prompt workflow to the specified URL 
# (http://127.0.0.1:8188/prompt) and queues it on the ComfyUI server
# running at that address.
def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req =  request.Request("http://127.0.0.1:8188/prompt", data=data)
    request.urlopen(req)    
# ======================================================================

# read workflow api data from file and convert it into dictionary 
prompt_workflow = json.load(open('F:\\Python_workSpace\\batch_test\\test1.json', 'r', encoding='utf-8'))

# prompt_prefix = "masterpiece,best quality, highly detailed,"
prompt_list = []
prompt_list.append("3D rendered cartoon rat statue with plump body covered in intricate coin and peony patterns. Gold filigree headpiece accents round obsidian eyes, paws clutching jade ingot. Warm bronze-gold gradients on layered textures, floating against minimalist gray marble backdrop.")
prompt_list.append("Stylized 3D ox statue with geometric cloud motifs etched across muscular form. Gilded horns spiral into celestial maps, large amber eyes glowing softly. Rich caramel and gold patina contrasts with matte gray slate base, terrazzo-like texture details.")
prompt_list.append("Cartoonish 3D tiger statue in dynamic crouching pose, striped fur rendered as layered flame scroll carvings. Gold leaf accents on forehead 'W' symbol, quartz pupils twinkling playfully. Warm copper and sepia tones pop against oxidized silver background.")
prompt_list.append("3D cartoon rabbit statue with jade-inlaid eyes, curled ears engraved with moon phase patterns. Body textured like cloisonné lotus vines, paws hugging pearl-studded crescent. Soft champagne gold hues glow against brushed concrete gray.")
prompt_list.append("Whimsical 3D dragon statue coiled around crystal orb, scales carved with interlocking dragon-phoenix motifs. Gold-plated whiskers frame glowing citrine eyes, tail tapered into fractal cloud patterns. Rich amber gradients on hammered metal texture.")
prompt_list.append("3D stylized snake statue with body coiled into infinity symbol, skin textured with bat and gourd engravings. Gold-capped fangs peek from smiling mouth, emerald eyes reflecting art deco patterns. Burnished brass tones contrast deep gray granite base.")
prompt_list.append("Dynamic 3D horse statue mid-gallop, mane flowing as carved cloud ribbons. Gilded horseshoes sparkle against caramel patina body, large onyx eyes framed by gold leaf lashes. Geometric chevron patterns add modern edge to antique bronze aesthetic.")
prompt_list.append("3D cartoon ram statue with horns spiraling into floral scrollwork, wool textured with Celtic knot patterns. Gold-hooved feet stand on jade '吉祥' plaque, oversized topaz eyes radiating warmth. Distressed gold leaf finish over layered ceramic textures.")
prompt_list.append("Playful 3D monkey statue balancing on one paw, body engraved with peach and longevity symbols. Gold crown tilts over glowing amber eyes, tail curled into '寿' character. Textured bronze finish mimics aged temple bells, pops against fluted gray column.")
prompt_list.append("3D stylized rooster statue with feather patterns laser-cut into metallic lattice. Gold comb and wattles contrast gunmetal gray body, oversized ruby eyes reflect intricate sundial patterns. Geometric art nouveau styling meets traditional cloisonné textures.")
prompt_list.append("3D guardian dog statue with chainmail texture etched in gold, paws resting on bone-shaped jade. Enlarged sapphire eyes glow under armored brow, tail carved into key and lock motifs. Distressed bronze finish over layered Damascus steel patterns.")
prompt_list.append("3D chubby pig statue with body covered in coin and ingot reliefs. Gold-ringed eyes squint with contentment, snout upturned to spray golden confetti. Antique brass patina over hammered metal texture, stands out against slate gray plinth.")

# give some easy-to-remember names to the nodes
ksampler_node = prompt_workflow["3"]
chkpoint_loader_node = prompt_workflow["4"]
lora_loader_node = prompt_workflow["10"]
latent_img_node = prompt_workflow["5"]
prompt_pos_node = prompt_workflow["14"]
save_image_node = prompt_workflow["19"]

# load the checkpoint that we want. 
# chkpoint_loader_node["inputs"]["ckpt_name"] = "sd1.5\\dreamshaper_8.safetensors"

lora_loader_node["inputs"]["lora_name"]= "FluxMythP0rtr4itStyle.safetensors"

# set image dimensions and batch size in EmptyLatentImage node
latent_img_node["inputs"]["width"] = 720
latent_img_node["inputs"]["height"] = 1024
# each prompt will produce a batch of 2 images
latent_img_node["inputs"]["batch_size"] = 2

# for every prompt in prompt_list...
for index, prompt in enumerate(prompt_list):

  # set the text prompt for positive CLIPTextEncode node
  # prompt_pos_node["inputs"]["text"] = prompt_prefix + prompt
  prompt_pos_node["inputs"]["text"] =  prompt

  # set a random seed in KSampler node 
  ksampler_node["inputs"]["seed"] = random.randint(1, 18446744073709551614)

  # set filename prefix to be the same as prompt
  # (truncate to first 100 chars if necessary)
  fileprefix =  prompt
  if len(fileprefix) > 20:
    fileprefix = fileprefix[:20]
  
  save_image_node["inputs"]["filename_prefix"] ='可爱动物雕塑_' + fileprefix
  queue_prompt(prompt_workflow)
    


  

