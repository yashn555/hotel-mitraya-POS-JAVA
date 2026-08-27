# Hotel Mitraya — Smart PDF Bill Generation System

A mobile-friendly, responsive Web & PDF Bill Generator built for **Hotel Mitraya**. Allows bill creation, live calculations, automated Indian currency conversion in words, instant DOCX-to-PDF conversion, and organized storage in the dedicated `/bills` directory.

---

## 🌟 Key Features

1. **📱 Responsive Mobile & Desktop Web App**:
   - Designed for smartphones, tablets, and desktop browsers.
   - Touch-optimized item adder with auto-calculations (Item Totals, Subtotal, Discount, Grand Total, and Amount in Words).
   - "Quick Add" food menu presets (Dahi Dhapata, Biryani Plate, Thali, Water, Cold Drinks, etc.).
   - Dark & Light mode toggle.
   - WhatsApp 1-click share button for generated bills.

2. **📁 Dedicated `/bills` Folder Storage**:
   - Every bill is automatically saved as a PDF with the standard naming convention:
     `bills/<Customer_Name>_<Bill_Number>.pdf`
   - In-app "Saved Bills" drawer with real-time search, download, inline preview, and deletion.

3. **📄 Direct PDF Output (No manual Word conversion needed)**:
   - Populates Word `template.docx` XML table placeholders seamlessly.
   - Automatically converts DOCX into high-quality PDF.
   - Supports Windows MS Word COM automation, LibreOffice, and cross-platform converters.

---

## 🚀 How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Web Server
```bash
python app.py
```
Open `http://localhost:5055` in your browser.

### 3. Open on Mobile Device on Local WiFi
When running on your computer, you can open the bill generator directly from your mobile phone connected to the same Wi-Fi:
```
http://<YOUR_COMPUTER_LOCAL_IP>:5055
```
*(Your local IP will be displayed in the terminal output upon running `app.py`)*

---

## ☁️ How to Host on Vercel

The project is pre-configured with `vercel.json` for seamless 1-click deployment on **Vercel**:

### Option 1: Via Vercel CLI
1. Install Vercel CLI (if not already installed):
   ```bash
   npm i -g vercel
   ```
2. In this project directory, run:
   ```bash
   vercel
   ```
3. Follow the CLI prompts to deploy.

### Option 2: Via Vercel Web Dashboard (GitHub)
1. Push this repository to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com) and click **"Add New Project"**.
3. Import your GitHub repository.
4. Click **Deploy**. Vercel will automatically detect `vercel.json` and deploy the Python app.

---

## 📂 Project Structure

```
├── app.py                     # Flask web server & REST APIs
├── generate_bill_docx.py      # Core Word template engine & PDF converter
├── template.docx              # Master Word bill template
├── bills/                     # Dedicated folder for generated PDF bills
├── templates/
│   └── index.html             # Responsive mobile-first frontend HTML
├── static/
│   ├── style.css              # Glassmorphic modern responsive styling
│   └── app.js                 # Dynamic calculations & API controller
├── requirements.txt           # Python dependencies
├── vercel.json                # Vercel deployment configuration
├── test_suite.py              # Automated verification test suite
└── README.md
```

---

## 🔌 API Reference

- `GET /` — Serves the responsive billing interface.
- `GET /api/health` — System status & template check.
- `GET /api/next-bill-no` — Calculates the next sequential bill number.
- `POST /api/bills/generate` — Generates a PDF bill and saves it to `/bills`.
- `GET /api/bills` — Lists all saved bills in `/bills` (supports `?q=` search query).
- `GET /api/bills/download/<filename>` — Downloads the PDF file.
- `GET /api/bills/preview/<filename>` — Streams the PDF file inline for browser/mobile view.
- `DELETE /api/bills/<filename>` — Deletes a bill from `/bills`.
