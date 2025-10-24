# Frontend - Couple Face-Swap

React + TypeScript frontend for the couple face-swap service.

## Tech Stack

- React 18+
- TypeScript
- Vite (build tool)
- Ant Design (UI library)
- Axios (HTTP client)

## Setup

### Install Dependencies

```bash
npm install
```

### Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to point to your backend API:

```env
VITE_API_URL=http://localhost:8000
```

## Development

### Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   ├── ImageUploader.tsx
│   │   ├── TemplateGallery.tsx
│   │   └── TaskProgress.tsx
│   ├── pages/            # Page components
│   │   └── FaceSwapWorkflow.tsx
│   ├── services/         # API clients
│   │   └── api.ts
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── index.html            # HTML template
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript config
└── vite.config.ts        # Vite config
```

## Components

### ImageUploader

Handles image upload with preview and validation.

```tsx
<ImageUploader
  imageType="husband"
  label="Upload Husband's Photo"
  onUploadComplete={(imageData) => console.log(imageData)}
/>
```

### TemplateGallery

Displays available templates with category filtering.

```tsx
<TemplateGallery
  onSelect={(templateId) => console.log(templateId)}
  selectedId={selectedTemplateId}
/>
```

### TaskProgress

Shows real-time progress of face-swap task.

```tsx
<TaskProgress
  taskId={taskId}
  onComplete={(task) => console.log('Completed:', task)}
  onError={(error) => console.error('Failed:', error)}
/>
```

### FaceSwapWorkflow

Main workflow page with step-by-step process.

## API Integration

The frontend communicates with the backend via REST API. See `src/services/api.ts`:

```typescript
import { apiClient } from './services/api';

// Upload image
const image = await apiClient.uploadImage(file, 'source');

// Get templates
const templates = await apiClient.getTemplates('acg', 20, 0);

// Create face-swap task
const response = await apiClient.createFaceSwapTask({
  husband_image_id: 1,
  wife_image_id: 2,
  template_id: 3,
});

// Check task status
const status = await apiClient.getTaskStatus(taskId);
```

## Styling

- Uses Ant Design components
- Custom styles in `App.css` and `index.css`
- Responsive design for mobile, tablet, desktop

## Environment Variables

Available environment variables (`.env`):

- `VITE_API_URL`: Backend API base URL
- `VITE_APP_NAME`: Application name

## Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

## Troubleshooting

### API connection error

Make sure the backend is running:
```bash
cd backend
uvicorn app.main:app --reload
```

Check `VITE_API_URL` in `.env` matches your backend URL.

### Build errors

Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

### TypeScript errors

Check TypeScript configuration:
```bash
npm run tsc
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Code splitting for optimal loading
- Lazy loading for images
- Optimized production build with Vite

## License

See main project LICENSE file.
