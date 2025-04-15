from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
import ollama
import json
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)  # Create a thread pool for handling requests

def chat_view(request):
    if request.method == 'POST':
        try:
            prompt = request.POST.get('prompt')
            if not prompt:
                return JsonResponse({'error': 'No prompt provided'}, status=400)

            # Test Ollama connection
            try:
                ollama.list()
            except Exception as e:
                logger.error(f"Ollama connection error: {str(e)}")
                return JsonResponse({
                    'error': 'Could not connect to Ollama. Please make sure Ollama is running.'
                }, status=503)

            response = StreamingHttpResponse(
                stream_response(prompt),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except Exception as e:
            logger.error(f"Error in chat_view: {str(e)}")
            return JsonResponse({
                'error': f'An error occurred: {str(e)}'
            }, status=500)
    return render(request, 'chat.html')

def stream_response(prompt):
    try:
        buffer = ""
        chunk_size = 0
        
        # Validate the prompt
        if not prompt or len(prompt.strip()) == 0:
            yield f"data: {json.dumps({'error': 'Please enter a valid message'})}\n\n"
            return

        for chunk in ollama.generate(
            model='deepseek-r1',
            prompt=prompt,
            stream=True,
            options={
                'temperature': 0.7,
                'top_k': 40,
                'num_ctx': 4096,
                'num_thread': 4
            }
        ):
            if not chunk or 'response' not in chunk:
                continue
                
            text = chunk['response']
            if not text:
                continue
                
            buffer += text
            chunk_size += len(text)
            
            # Send complete words or sentences
            if chunk_size >= 2 or any(buffer.endswith(c) for c in [' ', '.', '!', '?', '\n']):
                try:
                    response_data = {'text': buffer}
                    yield f"data: {json.dumps(response_data)}\n\n"
                    chunk_size = 0
                    buffer = ""
                except Exception as e:
                    logger.error(f"Error encoding response: {str(e)}")
                    yield f"data: {json.dumps({'error': 'Error processing response'})}\n\n"
                    return
        
        # Send any remaining buffer
        if buffer:
            try:
                yield f"data: {json.dumps({'text': buffer})}\n\n"
            except Exception as e:
                logger.error(f"Error encoding final buffer: {str(e)}")
                yield f"data: {json.dumps({'error': 'Error processing final response'})}\n\n"
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in stream_response: {error_msg}")
        if "connection refused" in error_msg.lower():
            yield f"data: {json.dumps({'error': 'Could not connect to Ollama. Please ensure Ollama is running.'})}\n\n"
        else:
            yield f"data: {json.dumps({'error': f'An error occurred: {error_msg}'})}\n\n"
