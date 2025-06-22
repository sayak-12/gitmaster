import keyring
from keyring.errors import PasswordDeleteError

SERVICE_NAME = "gitmaster"
OPENAI_KEY_NAME = "openai_api_key"
GEMINI_KEY_NAME = "gemini_api_key"
ANTHROPIC_KEY_NAME = "anthropic_api_key"
DEFAULT_KEY_NAME = "default_api_key"

def save_openai_key(key: str):
    keyring.set_password(SERVICE_NAME, OPENAI_KEY_NAME, key)
    _set_as_default_if_only_key("openai")

def get_openai_key() -> str | None:
    return keyring.get_password(SERVICE_NAME, OPENAI_KEY_NAME)

def delete_openai_key():
    try:
        keyring.delete_password(SERVICE_NAME, OPENAI_KEY_NAME)
    except PasswordDeleteError:
        # Password doesn't exist, which is fine
        pass
    _update_default_if_deleted("openai")

def save_gemini_key(key: str):
    keyring.set_password(SERVICE_NAME, GEMINI_KEY_NAME, key)
    _set_as_default_if_only_key("gemini")

def get_gemini_key() -> str | None:
    return keyring.get_password(SERVICE_NAME, GEMINI_KEY_NAME)

def delete_gemini_key():
    try:
        keyring.delete_password(SERVICE_NAME, GEMINI_KEY_NAME)
    except PasswordDeleteError:
        # Password doesn't exist, which is fine
        pass
    _update_default_if_deleted("gemini")

def save_anthropic_key(key: str):
    keyring.set_password(SERVICE_NAME, ANTHROPIC_KEY_NAME, key)
    _set_as_default_if_only_key("anthropic")

def get_anthropic_key() -> str | None:
    return keyring.get_password(SERVICE_NAME, ANTHROPIC_KEY_NAME)

def delete_anthropic_key():
    try:
        keyring.delete_password(SERVICE_NAME, ANTHROPIC_KEY_NAME)
    except PasswordDeleteError:
        # Password doesn't exist, which is fine
        pass
    _update_default_if_deleted("anthropic")

def get_all_keys() -> dict:
    """Get all stored API keys."""
    return {
        "openai": get_openai_key(),
        "gemini": get_gemini_key(),
        "anthropic": get_anthropic_key()
    }

def delete_all_keys():
    """Delete all stored API keys."""
    deleted_count = 0
    errors = []
    
    try:
        delete_openai_key()
        deleted_count += 1
    except Exception as e:
        errors.append(f"OpenAI: {str(e)}")
    
    try:
        delete_gemini_key()
        deleted_count += 1
    except Exception as e:
        errors.append(f"Gemini: {str(e)}")
    
    try:
        delete_anthropic_key()
        deleted_count += 1
    except Exception as e:
        errors.append(f"Anthropic: {str(e)}")
    
    # Also try to delete the default key setting
    try:
        keyring.delete_password(SERVICE_NAME, DEFAULT_KEY_NAME)
    except PasswordDeleteError:
        # Default key doesn't exist, which is fine
        pass
    except Exception as e:
        errors.append(f"Default key: {str(e)}")
    
    if errors:
        print(f"⚠️ Some keys could not be deleted: {', '.join(errors)}")
    
    return deleted_count

def get_default_key() -> str | None:
    """Get the currently set default API key."""
    default_service = keyring.get_password(SERVICE_NAME, DEFAULT_KEY_NAME)
    if not default_service:
        return None
    
    if default_service == "openai":
        return get_openai_key()
    elif default_service == "gemini":
        return get_gemini_key()
    elif default_service == "anthropic":
        return get_anthropic_key()
    return None

def get_default_service() -> str | None:
    """Get the name of the default service."""
    return keyring.get_password(SERVICE_NAME, DEFAULT_KEY_NAME)

def set_default_key(service: str):
    """Manually set the default API key service."""
    if service not in ["openai", "gemini", "anthropic"]:
        raise ValueError("Service must be 'openai', 'gemini', or 'anthropic'")
    
    # Check if the service has a key
    keys = get_all_keys()
    if not keys[service]:
        raise ValueError(f"No API key found for {service}")
    
    keyring.set_password(SERVICE_NAME, DEFAULT_KEY_NAME, service)

def _set_as_default_if_only_key(new_service: str):
    """Set the new service as default if it's the only key available."""
    keys = get_all_keys()
    available_keys = [service for service, key in keys.items() if key]
    
    if len(available_keys) == 1 and available_keys[0] == new_service:
        # This is the only key, set it as default
        keyring.set_password(SERVICE_NAME, DEFAULT_KEY_NAME, new_service)
    elif len(available_keys) > 1:
        # Multiple keys exist, set the newest one as default
        keyring.set_password(SERVICE_NAME, DEFAULT_KEY_NAME, new_service)

def _update_default_if_deleted(deleted_service: str):
    """Update default key if the deleted service was the default."""
    current_default = get_default_service()
    if current_default == deleted_service:
        # Default service was deleted, find another available key
        keys = get_all_keys()
        available_keys = [service for service, key in keys.items() if key]
        
        if available_keys:
            # Set the first available key as default
            keyring.set_password(SERVICE_NAME, DEFAULT_KEY_NAME, available_keys[0])
        else:
            # No keys left, remove default
            try:
                keyring.delete_password(SERVICE_NAME, DEFAULT_KEY_NAME)
            except PasswordDeleteError:
                # Default key doesn't exist, which is fine
                pass
