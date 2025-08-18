# LAMBO  
**Localized Automation for Barangay Optimization**

LAMBO is a digital solution designed to modernize barangay operations. It streamlines processes such as resident profiling, certificate issuance, and health records management using a Django backend with TailwindCSS and PostgreSQL.

---

## 🚀 After Cloning This Repository

Follow these steps to get started with development:

### STEP 1: Create a New Branch and Push It to GitHub

# Create and switch to a new branch
git checkout -b <branch_name>

# Push your branch to GitHub
git push origin <branch_name>



### STEP 2: Update Your Branch with the Latest From Main

# Fetch latest changes from the main branch
git fetch origin main

# Merge them into your current branch
git pull origin main



### STEP 3: Set Up Virtual Environment and Dependencies

# 1. Create virtual environment (recommended name: .venv)
py -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install Django and dependencies
pip install -r requirements.txt

# 4. Install Tailwind CSS dependencies
python manage.py tailwind install

# 5. Fix for "cross-env" not recognized (if error occurs)
npm install --save-dev cross-env


### STEP 4: Run Tailwind and Django Server in Separate Terminals

# Terminal 1 - Tailwind CSS
python manage.py tailwind start

# Terminal 2 - Django server
python manage.py runserver




### After Installing New Python Packages

pip freeze > requirements.txt