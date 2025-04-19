from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
import ollama
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import subprocess

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)  # Create a thread pool for handling requests

# Available models and their descriptions
AVAILABLE_MODELS = {
    'deepseek-r1': 'DeepSeek R1 - General purpose model',
    'llama2': 'Llama 2 - Meta\'s open source model',
    'mistral': 'Mistral - High performance model',
    'auto': 'Auto - Automatically selects the best model'
}

def get_available_models():
    """Get list of available models from Ollama using command line"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse the output to get model names
            lines = result.stdout.strip().split('\n')[1:]  # Skip header line
            model_list = [line.split()[0].split(':')[0] for line in lines if line.strip()]
            logger.info(f"Models from command line: {model_list}")
            return model_list
        else:
            logger.error(f"Error running ollama list: {result.stderr}")
            return ['deepseek-r1']  # Fallback to default model
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        return ['deepseek-r1']  # Fallback to default model

def select_best_model():
    """Select the best available model based on certain criteria"""
    available_models = get_available_models()
    preferred_models = ['mistral', 'llama2', 'deepseek-r1']
    
    for model in preferred_models:
        if model in available_models:
            return model
    
    return available_models[0] if available_models else 'deepseek-r1'

def chat_view(request):
    if request.method == 'POST':
        try:
            # Check if this is a model update request
            if request.POST.get('update_model') == 'true':
                model = request.POST.get('model', 'auto')
                request.session['selected_model'] = model
                # Clear any existing chat history in session
                if 'chat_history' in request.session:
                    del request.session['chat_history']
                return JsonResponse({'status': 'success', 'model': model})

            prompt = request.POST.get('prompt')
            model = request.POST.get('model', 'auto')
            
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

            # Handle auto model selection
            if model == 'auto':
                model = select_best_model()
                logger.info(f"Auto-selected model: {model}")

            # Ensure only one model is active
            logger.info(f"Using model: {model}")
            response = StreamingHttpResponse(
                stream_response(prompt, model),
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
    
    # GET request - return available models
    try:
        available_models = get_available_models()
        # Create a list of tuples with model name and description
        models_with_descriptions = []
        for model in available_models:
            description = AVAILABLE_MODELS.get(model, f"{model} - Custom model")
            models_with_descriptions.append((model, description))
        
        # Add auto option
        models_with_descriptions.insert(0, ('auto', AVAILABLE_MODELS['auto']))
        
        # Get the selected model from session or default to auto
        selected_model = request.session.get('selected_model', 'auto')
        
        return render(request, 'chat.html', {
            'models_with_descriptions': models_with_descriptions,
            'current_model': selected_model
        })
    except Exception as e:
        logger.error(f"Error in chat_view GET: {str(e)}")
        return render(request, 'chat.html', {
            'models_with_descriptions': [('deepseek-r1', AVAILABLE_MODELS['deepseek-r1'])],
            'current_model': 'deepseek-r1'
        })

def stream_response(prompt, model):
    try:
        buffer = ""
        chunk_size = 0
        
        # Validate the prompt
        if not prompt or len(prompt.strip()) == 0:
            yield f"data: {json.dumps({'error': 'Please enter a valid message'})}\n\n"
            return

        for chunk in ollama.generate(
            model=model,
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
