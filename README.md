# Eagle Eye 🦅  
**AI-Powered B2B SaaS for Online Review Management**

![Eagle Eye Banner](https://dummyimage.com/1200x300/222/fff&text=Eagle+Eye:+Your+AI+Eye+In+The+Sky)

---

## 🚀 Overview

**Eagle Eye** is a modern, scalable B2B SaaS platform that empowers businesses to manage their Google reviews with ease. Leveraging advanced AI (via Ollama and LLMs), Eagle Eye generates high-quality, context-aware responses to customer reviews, saving time and enhancing your brand's reputation.

- **AI-generated review responses** (customizable tone)
- **User authentication & multi-business support**
- **Beautiful, modern UI with dark mode**
- **Background task processing (Celery)**
- **Demo mode for instant product tours**
- **Fully containerized (Docker) for easy deployment**

---

## ✨ Features

- **AI-Powered Responses:** Generate smart, human-like replies to Google reviews using LLMs (Ollama, GPU support).
- **Multi-Business Dashboard:** Manage reviews for multiple businesses from a single account.
- **Modern UI:** Responsive, glassmorphic design with smooth dark mode toggle.
- **Secure & Scalable:** User authentication, background processing, and robust database design.
- **Demo Mode:** Instantly load demo data for product demos or testing.
- **Easy Deployment:** Docker & docker-compose for local or cloud deployment.

---

## 🖼️ Screenshots

| Dashboard | Review Page |
|-------------------|------------------|
| ![Dashboard](https://github.com/user-attachments/assets/55dbe9bd-31f1-446d-9d4e-acc44ded1e02) | ![Review Page](https://github.com/user-attachments/assets/7da61c5a-a847-4e12-9642-48f2f03c972c) |

---


## 🛠️ Tech Stack

- **Backend:** Python, Flask, Celery, PostgreSQL
- **Frontend:** Jinja2, HTML5, CSS3 (glassmorphism, gradients, animations)
- **AI:** Ollama (LLM, GPU support)
- **Auth:** Flask-Login
- **Deployment:** Docker, docker-compose

---

## ⚡ Quickstart

### 1. Clone the Repo

```bash
git clone https://github.com/yourusername/eagle-eye.git
cd eagle-eye
```

### 2. Configure Environment

Copy and edit `config.py` as needed (see comments in file).

### 3. Start with Docker

```bash
docker-compose up --build
```

- The app will be available at [http://localhost:5000](http://localhost:5000)
- Ollama AI service will run in a separate container (GPU supported)

### 4. Demo Mode

Visit `/demo` after logging in to instantly load demo data and try the app!

---

## 🤖 AI Model Setup

Eagle Eye uses [Ollama](https://ollama.com/) for local LLM inference.  
**To use AI features:**
- Make sure the Ollama container is running (`docker-compose up`)
- Pull your desired model (e.g., `deepseek-r1`) inside the Ollama container:
  ```bash
  ollama pull deepseek-r1
  ```
- Configure the model name in `config.py` if needed


## 🛡️ Security & Scalability

- Secure user authentication
- Background task processing (Celery)
- Scalable Dockerized architecture


## 🙌 Contributing

PRs and issues are welcome!  
Please open an issue to discuss your ideas or report bugs.


## 💡 Inspiration

Built to help businesses save time, respond faster, and build better customer relationships—powered by the latest in AI.
