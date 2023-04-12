import os
import requests
import re
from io import BytesIO
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import textwrap
import matplotlib.pyplot as plt
from shutil import which
import tempfile
import subprocess
from bs4 import BeautifulSoup
from pathlib import Path
import shutil
import gradio as gr
import io
from pdf2image import convert_from_path
from PIL import Image
from moviepy.editor import *
from PIL import Image
import tempfile
import os


def create_video(pil_image: Image, mp3_path: str, output_path: str):
    # Create a temporary file for the image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_image:
        pil_image.save(temp_image, format="PNG")
        temp_image_path = temp_image.name

    # Load the image and set its duration to match the audio duration
    image_clip = ImageClip(temp_image_path, duration=AudioFileClip(mp3_path).duration)

    # Set the fps attribute for the image clip
    image_clip.fps = 24

    # Set the audio to the image clip
    image_clip = image_clip.set_audio(AudioFileClip(mp3_path))

    # Write the video file
    image_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

    # Remove the temporary image file
    os.remove(temp_image_path)


def pdf_to_pil_images(pdf_path, dpi=200):
    # Convert the PDF to a sequence of PIL images
    pil_images = convert_from_path(pdf_path, dpi=dpi)
    return pil_images


def extract_arxiv_title(url):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("h1", class_="title mathjax").text.replace("Title:", "").strip()

    return title


def extract_arxiv_abstract(url):
    # Extract the arXiv paper ID from the URL
    paper_id = url.split("/")[-1]

    # Define the arXiv API URL
    arxiv_api_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"

    # Send a GET request to the arXiv API
    response = requests.get(arxiv_api_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(response.content)

        # Extract the abstract from the parsed XML
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text

        return abstract.strip()
    else:
        return f"Error: Unable to fetch data from arXiv API. Status code: {response.status_code}"


def text_to_speech(abstract, api_key):
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    headers = {
        "accept": "audio/mpeg",
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": abstract,
        "voice_settings": {"stability": 0, "similarity_boost": 0},
    }
    response = requests.post(url, headers=headers, json=payload)

    return response


def arxiv_abstract_to_speech(arxiv_url, api_key):
    abstract = extract_arxiv_abstract(arxiv_url)
    response = text_to_speech(abstract, api_key)
    return response


def abstract_to_pdf(title, abstract, output_filename):
    latex_template = r"""
    \documentclass{{standalone}}
    \usepackage[utf8]{{inputenc}}
    \usepackage{{amsmath}}
    \usepackage{{amssymb}}
    \usepackage{{hyperref}}
    \usepackage{{varwidth}}
    \usepackage{{adjustbox}}
    \begin{{document}}
    \begin{{adjustbox}}{{margin=5mm}}
    \begin{{varwidth}}{{\linewidth}}
    \textbf{{{title}}} \\
    {content}
    \end{{varwidth}}
    \end{{adjustbox}}
    \end{{document}}
    """

    latex_content = latex_template.format(title=title, content=abstract)

    with tempfile.TemporaryDirectory() as temp_dir:
        tex_file = Path(temp_dir) / "abstract.tex"
        pdf_file = Path(temp_dir) / "abstract.pdf"

        with open(tex_file, "w") as f:
            f.write(latex_content)

        subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-output-directory",
                temp_dir,
                tex_file,
            ],
            check=True,
        )

        shutil.copy(pdf_file, output_filename)


def generate_abstract(arxiv_url):
    paper_id = arxiv_url.split("/")[-1]
    title = extract_arxiv_title(arxiv_url)
    abstract = extract_arxiv_abstract(arxiv_url)

    pdf_filename = f"./tmp/{paper_id}.pdf"
    audio_filename = f"./tmp/{paper_id}.mp3"

    abstract_to_pdf(title, abstract, pdf_filename)

    # convert pdf to image
    abstract_image = pdf_to_pil_images(pdf_filename)[0]

    return abstract_image


def generate_audio(arxiv_url, api_key):
    paper_id = arxiv_url.split("/")[-1]
    audio_filename = f"./tmp/{paper_id}.mp3"

    response = arxiv_abstract_to_speech(arxiv_url, api_key)

    with open(audio_filename, "wb") as f:
        f.write(response.content)

    return audio_filename


def generate_video(arxiv_url):
    paper_id = arxiv_url.split("/")[-1]

    pdf_filename = f"./tmp/{paper_id}.pdf"
    audio_filename = f"./tmp/{paper_id}.mp3"
    movie_filename = f"./tmp/{paper_id}.mp4"

    abstract_image = pdf_to_pil_images(pdf_filename)[0]

    create_video(abstract_image, audio_filename, movie_filename)

    return movie_filename


# use blocks API
with gr.Blocks() as app:
    arxiv_link = gr.Textbox(
        label="paper link",
        lines=1,
        placeholder="https://arxiv.org/abs/2303.12712",
    )
    abstract_btn = gr.Button(label="Generate")
    output_image = gr.Image(label="abstract image")
    elevn_api_key = gr.Textbox(
        label="ElevenLabs API key", lines=1, placeholder="ElevenLabs API key"
    )
    audio_btn = gr.Button(label="Generate audio")
    output_audio = gr.Audio(
        label="abstract audio",
        type="filepath",
    )

    video_btn = gr.Button(label="Generate video")
    output_video = gr.Video()

    abstract_btn.click(generate_abstract, inputs=[arxiv_link], outputs=[output_image])
    audio_btn.click(
        generate_audio, inputs=[arxiv_link, elevn_api_key], outputs=[output_audio]
    )
    video_btn.click(generate_video, inputs=[arxiv_link], outputs=[output_video])


app.launch()
