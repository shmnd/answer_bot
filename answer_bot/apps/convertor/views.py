from django.shortcuts import render
from django.contrib import messages
from .models import MCQ
import json
from bs4 import BeautifulSoup
import re

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

def convert_mcqs(request):
    """
    View to handle MCQ JSON file uploads and conversion
    """
    mcqs = []
    error_message = None
    success_message = None
    
    if request.method == 'POST' and request.FILES.get('json_file'):
        try:
            json_file = request.FILES['json_file']
            
            try:
                data = json.load(json_file)
            except json.JSONDecodeError as e:
                error_message = f"Invalid JSON file: {str(e)}"
                return render(request, 'convertor/convert_upload.html', {
                    'mcqs': mcqs,
                    'error_message': error_message
                })
            
            # Parse the JSON data
            parsed_data = parse_question_json(data)
            
            # Save to database and collect for display
            for parsed_item in parsed_data:
                qid = parsed_item.pop('qid')  # Remove qid from defaults
                image_urls = parsed_item.pop('image_urls', [])  # Handle any fields not in your model
                question_text = parsed_item.pop('question_text', '')
                explanation_text = parsed_item.pop('explanation_text', '')
                
                # Add these back if your model has these fields
                # parsed_item['image_urls'] = image_urls
                # parsed_item['question_text'] = question_text
                # parsed_item['explanation_text'] = explanation_text
                
                MCQ.objects.update_or_create(qid=qid, defaults=parsed_item)
                mcqs.append({**parsed_item, 'qid': qid})  # Add qid back for display
            
            success_message = f"Successfully processed {len(mcqs)} MCQs"
            
        except Exception as e:
            error_message = f"Error processing file: {str(e)}"
    
    return render(request, 'convertor/convert_upload.html', {
        'mcqs': mcqs,
        'success_message': success_message,
        'error_message': error_message
    })