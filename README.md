# Green Price Tracker V2 - Multi-User Fresh Build Walkthrough

Your entirely new, completely fresh Green Price Tracker V2 has natively generated in the **`Desktop/GPT`** directory exactly as requested!

This build is vastly more sophisticated than the previous prototype. We moved entirely to a multi-tenant database schema, introduced comprehensive Flask Authentication with session protection, and brought a premium, visually stunning frontend packed with glassmorphism and real-time JavaScript analytics.

## 🔐 Authentication & Backend Architecture

### 1. Robust Registration & Login System
We created a fully secure `login_required` interface. Users can visit `/register` to generate an account (passwords are heavily salted and hashed locally using `werkzeug.security`).

### 2. Multi-User Database Relationships (`database.py`)
- We dropped global targets and migrated to a `user_products` mapping table structure!
- Now, when two totally identical links are posted by different users (like the same Amazon iPhone trace), the **scraper only hits the server once during the nightly background scan**, keeping overhead dramatically low!
- Both users can then maintain distinct Target Prices independently for that same iPhone.

## 🎨 Design & Interactivity Upgrades

### 1. Premium Glassmorphic Aesthetic (`style.css`)
- Rebuilt from the ground up to utilize "frosted glass" containers via `backdrop-filter: blur()`. It provides extreme visual pop!
- Added `animate-float` macros for dynamic hover interactions on the Product Cards.
- Fluid animations dynamically scale containers into view.

### 2. Unified Analytics Dashboard 📊 (`index.html`)
The main dashboard has scaled significantly from just a tracking list:
- The top header immediately surfaces aggregate stat blocks based *strictly on your session*: Total tracked items, active good deal counts, and a compiled "Average Eco Score" highlighting your personal footprint tracking.

### 3. Integrated JavaScript Previews (`main.js`)
- The "Paste -> Preview" is even smoother, utilizing decoupled generic fetch requests (`/api/preview`) protected behind authentication walls.
- Graphing data natively uses current HTML5 `<canvas>` tags interacting natively with custom `--primary-color` theme injections to match light/dark mode instantly.

## 🚀 How to Launch Your New App
To access your completely fresh V2 deployment:
1. Open up a terminal.
2. Navigate into the new GPT directory: `cd c:/Users/hp/OneDrive/Desktop/GPT`
3. Automatically install our requirements and the `werkzeug` package needed for hashing:
   ```bash
   pip install -r requirements.txt
   ```
4. Run your application!
   ```bash
   python app.py
   ```

*You can open your browser to `http://127.0.0.1:5000` to dive into the stunning new split-view login interfaces!*
