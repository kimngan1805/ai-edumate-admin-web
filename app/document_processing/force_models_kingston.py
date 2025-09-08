#!/usr/bin/env python3
"""
Force tất cả AI models download và cache về Kingston thay vì Mac
"""
import os
import sys
import shutil
from pathlib import Path

def move_existing_models_to_kingston():
    """Di chuyển models đã download từ Mac sang Kingston"""
    
    kingston_cache = Path("/Volumes/KINGSTON/.ai_models_cache")
    kingston_cache.mkdir(exist_ok=True)
    
    # Các thư mục cache thường gặp trên Mac
    mac_cache_dirs = [
        Path.home() / ".cache" / "huggingface",
        Path.home() / ".cache" / "torch", 
        Path.home() / ".cache" / "transformers",
        Path("/tmp") / "torch_extensions",
        Path.home() / ".cache" / "pip",
        Path("/var/folders") # System temp folders
    ]
    
    moved_size = 0
    
    for cache_dir in mac_cache_dirs:
        if cache_dir.exists():
            target = kingston_cache / cache_dir.name
            
            try:
                if cache_dir.name == "folders":
                    # Skip system folders - just report size
                    size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    moved_size += size
                    print(f"⚠️  System cache detected: {cache_dir} ({size/1024/1024:.1f}MB)")
                else:
                    # Move cache directories
                    if target.exists():
                        shutil.rmtree(target)
                    
                    shutil.move(str(cache_dir), str(target))
                    size = sum(f.stat().st_size for f in target.rglob('*') if f.is_file())
                    moved_size += size
                    
                    print(f"📦 Moved: {cache_dir} → {target} ({size/1024/1024:.1f}MB)")
                    
            except Exception as e:
                print(f"⚠️  Cannot move {cache_dir}: {e}")
    
    print(f"💾 Total moved: {moved_size/1024/1024/1024:.2f}GB to Kingston")
    return moved_size

def setup_kingston_ai_environment():
    """Setup environment để force AI models về Kingston"""
    
    kingston_base = Path("/Volumes/KINGSTON")
    if not kingston_base.exists():
        print("❌ Kingston drive not found!")
        sys.exit(1)
    
    # Tạo cache directories trên Kingston
    ai_cache = kingston_base / ".ai_models_cache"
    ai_cache.mkdir(exist_ok=True)
    
    cache_dirs = {
        'huggingface': ai_cache / "huggingface",
        'torch': ai_cache / "torch", 
        'transformers': ai_cache / "transformers",
        'torch_extensions': ai_cache / "torch_extensions",
        'pip': ai_cache / "pip",
        'temp': kingston_base / "temp",
        'matplotlib': ai_cache / "matplotlib",
        'home': kingston_base / "fake_home"
    }
    
    for name, path in cache_dirs.items():
        path.mkdir(exist_ok=True, parents=True)
    
    # Set environment variables để redirect tất cả cache
    env_setup = {
        # Hugging Face models
        'HF_HOME': str(cache_dirs['huggingface']),
        'HF_DATASETS_CACHE': str(cache_dirs['huggingface'] / "datasets"),
        'TRANSFORMERS_CACHE': str(cache_dirs['transformers']),
        'HF_HUB_CACHE': str(cache_dirs['huggingface'] / "hub"),
        
        # PyTorch models
        'TORCH_HOME': str(cache_dirs['torch']),
        'TORCH_HUB': str(cache_dirs['torch'] / "hub"),
        'TORCH_EXTENSIONS_DIR': str(cache_dirs['torch_extensions']),
        'PYTORCH_KERNEL_CACHE_PATH': str(cache_dirs['torch'] / "kernels"),
        
        # System temp directories
        'TMPDIR': str(cache_dirs['temp']),
        'TEMP': str(cache_dirs['temp']),
        'TMP': str(cache_dirs['temp']),
        'HOME': str(cache_dirs['home']),  # Fake home directory
        
        # Matplotlib và visualization
        'MPLCONFIGDIR': str(cache_dirs['matplotlib']),
        'MPLBACKEND': 'Agg',  # No GUI backend
        
        # Pip cache
        'PIP_CACHE_DIR': str(cache_dirs['pip']),
        
        # Python user packages
        'PYTHONUSERBASE': str(kingston_base / "python_user"),
        
        # Conda/pip installs
        'CONDA_PKGS_DIRS': str(kingston_base / "conda_pkgs"),
        
        # Additional AI frameworks
        'SENTENCE_TRANSFORMERS_HOME': str(cache_dirs['huggingface'] / "sentence_transformers"),
        'SPACY_DATA': str(ai_cache / "spacy"),
    }
    
    print("🔧 Setting up Kingston AI environment...")
    for key, value in env_setup.items():
        os.environ[key] = value
        Path(value).mkdir(exist_ok=True, parents=True)
        print(f"   {key} → Kingston")
    
    # Create symbolic links từ Mac cache folders về Kingston (backup plan)
    mac_home = Path.home()
    
    try:
        mac_cache = mac_home / ".cache"
        if mac_cache.exists() and not mac_cache.is_symlink():
            # Backup existing cache
            backup_cache = mac_home / ".cache_backup"
            if backup_cache.exists():
                shutil.rmtree(backup_cache)
            shutil.move(str(mac_cache), str(backup_cache))
            print(f"📦 Backed up Mac cache to: {backup_cache}")
        
        # Create symlink to Kingston
        if not mac_cache.exists():
            mac_cache.symlink_to(ai_cache)
            print(f"🔗 Created symlink: {mac_cache} → {ai_cache}")
            
    except Exception as e:
        print(f"⚠️  Could not create symlink: {e}")
    
    print(f"✅ Kingston AI environment ready!")
    print(f"   📍 AI Models will be cached to: {ai_cache}")
    print(f"   💾 Available space: {shutil.disk_usage(kingston_base)[2]/1024/1024/1024:.1f}GB")

def test_ai_model_download():
    """Test download một model nhỏ để xem có cache đúng chỗ không"""
    
    print("\n🧪 Testing AI model download to Kingston...")
    
    try:
        # Test với transformers (model nhỏ)
        from transformers import AutoTokenizer
        
        print("📥 Downloading small test model...")
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        print("✅ Model downloaded successfully!")
        
        # Check xem có cache trên Kingston không
        kingston_cache = Path("/Volumes/KINGSTON/.ai_models_cache/huggingface")
        if any(kingston_cache.rglob("*distilbert*")):
            print("✅ Model cached on Kingston!")
            return True
        else:
            print("❌ Model NOT cached on Kingston")
            return False
            
    except Exception as e:
        print(f"❌ Model download test failed: {e}")
        return False

def check_mac_space():
    """Kiểm tra dung lượng ổ Mac"""
    
    mac_usage = shutil.disk_usage("/")
    free_gb = mac_usage[2] / 1024 / 1024 / 1024
    
    print(f"\n💽 Mac Storage Status:")
    print(f"   • Free space: {free_gb:.1f}GB")
    
    if free_gb < 5:
        print("⚠️  WARNING: Very low disk space on Mac!")
        return False
    elif free_gb < 10:
        print("⚠️  CAUTION: Low disk space on Mac")
        return True
    else:
        print("✅ Sufficient space on Mac")
        return True

def main():
    """Main setup function"""
    
    print("🚀 FORCE AI MODELS TO KINGSTON")
    print("=" * 50)
    
    # Check Mac space first
    mac_ok = check_mac_space()
    
    # Check Kingston availability
    kingston = Path("/Volumes/KINGSTON")
    if not kingston.exists():
        print("❌ Kingston drive not found!")
        return
    
    kingston_usage = shutil.disk_usage(kingston)
    kingston_free = kingston_usage[2] / 1024 / 1024 / 1024
    print(f"📦 Kingston free space: {kingston_free:.1f}GB")
    
    if kingston_free < 20:
        print("⚠️  WARNING: Kingston may not have enough space for AI models")
    
    # Move existing models if any
    print("\n1. Moving existing AI models to Kingston...")
    moved_size = move_existing_models_to_kingston()
    
    # Setup environment
    print("\n2. Setting up Kingston AI environment...")
    setup_kingston_ai_environment()
    
    # Test model download
    print("\n3. Testing model download...")
    test_success = test_ai_model_download()
    
    # Summary
    print(f"\n🎯 SETUP COMPLETE")
    print("=" * 30)
    print(f"   • Mac space ok: {'✅' if mac_ok else '❌'}")
    print(f"   • Models moved: {moved_size/1024/1024/1024:.2f}GB")
    print(f"   • Environment setup: ✅")
    print(f"   • Test download: {'✅' if test_success else '❌'}")
    
    if test_success:
        print("\n🎉 SUCCESS! AI models will now cache to Kingston!")
        print("📝 You can now run your processing scripts safely.")
        print("\n💡 Next steps:")
        print("   cd /Volumes/KINGSTON/document_processing/documents_processing")
        print("   python test.py")
    else:
        print("\n🔧 Some issues detected. Check the setup above.")

if __name__ == "__main__":
    main()
