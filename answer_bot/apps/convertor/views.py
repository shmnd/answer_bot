import re
import os
import fitz
import json
from docx import Document
import requests
from django.core.files.base import ContentFile
from django.shortcuts import render
from apps.questions.models import ImprovedResponse
from bs4 import BeautifulSoup
from django.contrib import messages


def download_and_attach_image(question_obj, image_url):
    """
    Downloads an image from the URL and attaches it to the question's ImageField.
    """
    if not image_url or not image_url.startswith("http"):
        print(f"⚠️ Skipped invalid image URL: '{image_url}'")
        return

    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            filename = image_url.split("/")[-1]
            question_obj.image.save(filename, ContentFile(response.content), save=True)
    except Exception as e:
        print(f"⚠️ Failed to attach image from {image_url}: {e}")


def clean_html(raw_html):
    """
    Extract text from HTML while preserving basic structure with newlines
    """
    if not raw_html:
        return ""
    
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Replace paragraph tags with double newlines
    for tag in soup.find_all('p'):
        tag.replace_with(f"{tag.get_text()}\n\n")
    
    # Replace list items with newlines and bullet points
    for tag in soup.find_all('li'):
        tag.replace_with(f"• {tag.get_text()}\n")
    
    # Replace headings with uppercase text and newlines
    for i in range(1, 7):
        for tag in soup.find_all(f'h{i}'):
            tag.replace_with(f"\n{tag.get_text().upper()}\n")
    
    # Get the text
    text = soup.get_text(separator=" ", strip=True)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def clean_option_text(option_text):
    """
    Clean option text by removing extra whitespace, newlines, and HTML
    """
    if not option_text:
        return ""
    
    # Remove HTML if present
    soup = BeautifulSoup(option_text, "html.parser")
    text = soup.get_text(" ", strip=True)
    
    # Remove newlines and multiple spaces
    clean_text = re.sub(r'\s+', ' ', text).strip()
    
    return clean_text


def extract_images(html_content):
    """
    Extract image URLs from HTML content
    """
    images = []
    if not html_content:
        return images
    
    soup = BeautifulSoup(html_content, "html.parser")
    for img in soup.find_all('img'):
        if 'src' in img.attrs:
            images.append(img['src'])
    
    return images


def parse_question_json(data):
    """
    Parse JSON data and return list of parsed MCQ dictionaries
    """
    parsed = []
    processed_count = 0
    skipped_count = 0

    for entry in data:
        if "data" not in entry:
            skipped_count += 1
            continue
            
        for item in entry["data"]:
            # Ensure 'qid' is present, or skip the item
            qid = item.get('qid', None)
            if not qid:
                skipped_count += 1
                continue
            
            # Clean options
            option_a = clean_option_text(item.get('opa', ''))
            option_b = clean_option_text(item.get('opb', ''))
            option_c = clean_option_text(item.get('opc', ''))
            option_d = clean_option_text(item.get('opd', ''))
            
            # Extract plain text and images
            question_html = item.get("question", "")
            question_text = clean_html(question_html)
            question_images = extract_images(question_html)
            
            explanation_html = item.get("exp", "")
            explanation_text = clean_html(explanation_html)
            explanation_images = extract_images(explanation_html)
            
            # Combine all images
            all_images = question_images + explanation_images
            
            parsed_item = {
                "qid": qid,
                "subject": item.get("subject", ""),
                "question": question_html,
                "question_text": question_text,  # Add cleaned text version
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_d": option_d,
                "correct_option": item.get('cop', ''),
                "explanation": explanation_html,
                "explanation_text": explanation_text,  # Add cleaned text version
                "image_urls": all_images,  # Add extracted image URLs
            }
            parsed.append(parsed_item)
            processed_count += 1

    print(f"Processed {processed_count} questions, skipped {skipped_count}")
    return parsed


CHUNK_SIZE = 1000  # number of questions to insert at a time

def chunkify(data_list, chunk_size):
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]


def convert_mcqs(request):
    """
    Accepts and parses uploaded MCQ files (PDF, TXT, JSON, DOCX) and uploads in chunks.
    """
    mcqs = []
    error_message = None
    success_message = None

    if request.method == 'POST' and request.FILES.get('file'):
        try:
            uploaded_file = request.FILES['file']
            file_name = uploaded_file.name
            ext = os.path.splitext(file_name)[1].lower()

            content = ""

            if ext == ".json":
                try:
                    data = json.load(uploaded_file)
                    parsed_data = parse_question_json(data)

                    for chunk in chunkify(parsed_data, CHUNK_SIZE):
                        for parsed_item in chunk:
                            qid = parsed_item['qid']
                            correct_answer = parsed_item['correct_option']
                            question = parsed_item['question_text']
                            explanation = parsed_item['explanation_text']
                            image_urls = parsed_item['image_urls']

                            q_obj, created = Questions.objects.update_or_create(
                                qid=qid,
                                defaults={
                                    "correct_answer": correct_answer,
                                    "question": question,
                                    "explanation": explanation,
                                    "user": request.user
                                }
                            )

                            if created and image_urls:
                                download_and_attach_image(q_obj, image_urls[0])
                            mcqs.append({**parsed_item, 'qid': qid})

                            messages.success(request, "File uploaded successfully") 


                except json.JSONDecodeError as e:
                    error_message = f"Invalid JSON file: {str(e)}"

            elif ext in [".txt", ".pdf", ".docx"]:
                # Read content from TXT / PDF / DOCX
                if ext == ".txt":
                    content = uploaded_file.read().decode("utf-8")
                elif ext == ".pdf":
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    content = "\n".join([page.get_text() for page in doc])
                elif ext == ".docx":
                    document = Document(uploaded_file)
                    content = "\n".join([para.text for para in document.paragraphs])

                # Split by double newline (basic question splitting)
                questions = [q.strip() for q in content.split("\n\n") if q.strip()]
                
                for chunk in chunkify(questions, CHUNK_SIZE):
                    bulk_objects = []
                    for q in chunk:
                        bulk_objects.append(Questions(
                            question=q,
                            user=request.user
                        ))
                    Questions.objects.bulk_create(bulk_objects)

                success_message = print(f"Data saved successfully")
            else:
                error_message = f"❌ Unsupported file type: {ext}"

        except Exception as e:
            error_message = f"❌ Error processing file: {str(e)}"

    return render(request, 'convertor/convert_upload.html', {
        'success_message': success_message,
        'error_message': error_message
    })
