# AIMirror Dashboard

React + Vite dashboard for visualizing Instagram Reels behavioral data.

## 🚀 Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment (Optional)

Create a `.env` file if you need to change the API URL:

```env
VITE_API_URL=http://localhost:3000
```

### 3. Run Development Server

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

## 📊 Features

### Overview Page
- Total sessions and reels watched
- Total watch time statistics
- Like ratio and engagement metrics
- Top 5 most watched creators (bar chart)
- Engagement distribution (pie chart)

### Sessions Page
- List all tracking sessions
- View session duration and event count
- Delete individual sessions
- Navigate to detailed session view

### Session Detail Page
- Complete session information
- Watch time timeline chart
- Full event list with timestamps
- Like/replay statistics per reel

### Analytics Page
- Comprehensive behavioral metrics
- Time-based analytics
- Engagement statistics
- Top creators ranking table

## 🎨 Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **date-fns** - Date formatting

## 🔧 API Integration

The dashboard connects to the FastAPI backend at `http://localhost:3000` by default.

Make sure the backend is running before starting the dashboard.

## 📱 Responsive Design

The dashboard is fully responsive and works on:
- Desktop (1400px+)
- Tablet (768px - 1400px)
- Mobile (< 768px)

## 🎨 Customization

### Colors

Edit `src/index.css` to customize the color scheme:

```css
:root {
  --primary: #667eea;
  --secondary: #764ba2;
  /* ... other colors */
}
```

### Charts

Charts are built with Recharts. Customize them in the respective page components:
- `src/pages/Overview.jsx`
- `src/pages/SessionDetail.jsx`
