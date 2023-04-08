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


def extract_arxiv_abstract(url):
  # Extract the arXiv paper ID from the URL
  paper_id = url.split('/')[-1]

  # Define the arXiv API URL
  arxiv_api_url = f'http://export.arxiv.org/api/query?id_list={paper_id}'

  # Send a GET request to the arXiv API
  response = requests.get(arxiv_api_url)

  # Check if the request was successful
  if response.status_code == 200:
    # Parse the XML response
    root = ET.fromstring(response.content)

    # Extract the abstract from the parsed XML
    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
      abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text

    return abstract.strip()
  else:
    return f'Error: Unable to fetch data from arXiv API. Status code: {response.status_code}'


def text_to_speech(abstract, api_key):
  url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
  headers = {
    "accept": "audio/mpeg",
    "xi-api-key": api_key,
    "Content-Type": "application/json"
  }
  payload = {
    "text": abstract,
    "voice_settings": {
      "stability": 0,
      "similarity_boost": 0
    }
  }
  response = requests.post(url, headers=headers, json=payload)

  return response


def arxiv_abstract_to_speech(arxiv_url, api_key):
  abstract = extract_arxiv_abstract(arxiv_url)
  response = text_to_speech(abstract, api_key)
  return response


def abstract_to_pdf(abstract, output_filename='abstract.pdf'):
  if not which("pdflatex"):
    raise Exception("pdflatex not found. Please install TeX Live or MiKTeX.")

  latex_template = r"""
        \documentclass{{standalone}}
        \usepackage[utf8]{{inputenc}}
        \usepackage{{amsmath}}
        \usepackage{{amssymb}}
        \usepackage{{hyperref}}
        \usepackage{{varwidth}}
        \begin{{document}}
        \begin{{varwidth}}{{\linewidth}}
        {content}
        \end{{varwidth}}
        \end{{document}}
        """

  latex_content = latex_template.format(content=abstract)

  with tempfile.TemporaryDirectory() as temp_dir:
    tex_file = os.path.join(temp_dir, "abstract.tex")
    with open(tex_file, "w") as f:
      f.write(latex_content)

    cmd = [
      "pdflatex", "-interaction=batchmode", "-output-directory", temp_dir,
      tex_file
    ]
    subprocess.run(cmd, check=True)

    pdf_file = os.path.join(temp_dir, "abstract.pdf")
    os.rename(pdf_file, output_filename)


# Example usage:
arxiv_url = 'https://arxiv.org/abs/2304.03279'
api_key = 'xXx'

# response = arxiv_abstract_to_speech(arxiv_url, api_key)
# print(response.status_code)

# # Save the response content (audio file) to disk
# with open('abstract.mp3', 'wb') as f:
#   f.write(response.content)

abstract = extract_arxiv_abstract(arxiv_url)
abstract_to_pdf(abstract, 'abstractx.pdf')
