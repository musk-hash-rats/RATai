import os

def load_env_manual():
    """
    Manually loads .env file to avoid python-dotenv parsing issues.
    Sets variables in os.environ and returns a dictionary of them.
    """
    env_vars = {}
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if not os.path.exists(env_path):
             # Try current directory if relative path fails (e.g. running from root)
             env_path = '.env'
             
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Helper to strip common quote styles
                    value = value.strip().strip("'").strip('"')
                    env_vars[key.strip()] = value
                    
        # Set os.environ
        for k, v in env_vars.items():
            os.environ[k] = v
            
    except Exception as e:
        print(f"Warning: Error reading .env manually: {e}")
    return env_vars
