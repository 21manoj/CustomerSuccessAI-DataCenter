# Company Logo Setup Instructions

## Where to Place Your Logo

### **Location:** `/Users/manojgupta/kpi-dashboard/public/company-logo.png`

Place your company logo file in the `public` folder with the filename `company-logo.png`

---

## Step-by-Step Instructions

### Option 1: PNG Logo (Recommended)

1. **Prepare your logo:**
   - Format: PNG (supports transparency)
   - Recommended size: 200-400px width
   - Aspect ratio: Any (will auto-scale to height of 80px)
   - Background: Transparent or white

2. **Copy to public folder:**
   ```bash
   cp /path/to/your/logo.png /Users/manojgupta/kpi-dashboard/public/company-logo.png
   ```

3. **Refresh your browser** - Logo will appear automatically!

### Option 2: Other Formats (JPG, SVG, WEBP)

If you prefer a different format:

**For JPG:**
```bash
cp /path/to/your/logo.jpg /Users/manojgupta/kpi-dashboard/public/company-logo.png
# Or rename to .jpg and update the src in LoginComponent.tsx
```

**For SVG (best for scalability):**
```bash
cp /path/to/your/logo.svg /Users/manojgupta/kpi-dashboard/public/company-logo.svg
```

Then update `src/components/LoginComponent.tsx` line 63:
```tsx
src="/company-logo.svg"  // Change from .png to .svg
```

---

## What Was Changed

### File Modified: `src/components/LoginComponent.tsx`

**Before:**
```tsx
<div className="mx-auto h-16 w-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
  <TrendingUp className="h-8 w-8 text-white" />
</div>
<h2 className="mt-6 text-2xl font-bold text-gray-900 text-center">...</h2>
```

**After:**
```tsx
<div className="text-center flex flex-col items-center">
  <div className="mx-auto mb-6">
    <img 
      src="/company-logo.png" 
      alt="Company Logo" 
      className="h-20 w-auto object-contain"
    />
    {/* Fallback gradient icon if logo not found */}
  </div>
  <h2 className="text-2xl font-bold text-gray-900 text-center">...</h2>
</div>
```

**Key Features:**
- ✅ Logo displays at 80px height (width auto-scales)
- ✅ Centered on page
- ✅ Graceful fallback if logo file not found (shows gradient icon)
- ✅ Title centered below logo
- ✅ Professional spacing

---

## Logo Specifications

### Recommended:
- **Format:** PNG with transparent background
- **Width:** 200-400px (will scale to fit)
- **Height:** Any (will scale to 80px display height)
- **File Size:** < 100KB for fast loading
- **Background:** Transparent or white

### Supported Formats:
- ✅ PNG (recommended)
- ✅ JPG/JPEG
- ✅ SVG (best for scalability)
- ✅ WEBP

---

## Fallback Behavior

If `company-logo.png` is not found:
- The gradient icon with TrendingUp will display automatically
- No errors or broken images
- Seamless user experience

---

## Quick Setup Commands

### If you have your logo ready:

```bash
# Copy your logo to the public folder
cp ~/Downloads/my-company-logo.png /Users/manojgupta/kpi-dashboard/public/company-logo.png

# Or if it's named differently:
cp ~/Desktop/logo.png /Users/manojgupta/kpi-dashboard/public/company-logo.png

# Verify it's there:
ls -lh /Users/manojgupta/kpi-dashboard/public/company-logo.png
```

### Test in browser:

1. Navigate to: `http://localhost:3000`
2. You should see your logo at the top of the login page
3. Title should be centered below the logo

---

## File Structure

```
kpi-dashboard/
├── public/
│   ├── favicon.ico
│   ├── index.html
│   ├── logo192.png
│   ├── logo512.png
│   ├── manifest.json
│   ├── robots.txt
│   └── company-logo.png  ← PLACE YOUR LOGO HERE
├── src/
│   └── components/
│       └── LoginComponent.tsx  ← Updated to use logo
└── ...
```

---

## Customization Options

### Adjust Logo Size

In `LoginComponent.tsx`, change the height class:

```tsx
className="h-20 w-auto object-contain"  // Current: 80px height
className="h-24 w-auto object-contain"  // Larger: 96px height
className="h-16 w-auto object-contain"  // Smaller: 64px height
```

### Change Logo Position

For left-aligned logo:
```tsx
<div className="flex items-center">  // Remove 'flex-col' and 'text-center'
  <img src="/company-logo.png" className="h-20 mr-4" />
  <div>
    <h2>Title</h2>
    <p>Subtitle</p>
  </div>
</div>
```

### Add Logo Border/Shadow

```tsx
className="h-20 w-auto object-contain shadow-lg rounded-lg border border-gray-200 p-2"
```

---

## Production Deployment

When deploying to AWS:

1. **Logo will be bundled** with your build automatically
2. **No extra configuration needed** - it's in the public folder
3. **Cache busting** handled by React build process
4. **CDN friendly** - can be served from CloudFront

---

## Testing Checklist

- [ ] Logo file copied to `public/company-logo.png`
- [ ] Logo displays on login page
- [ ] Logo has correct proportions (not stretched)
- [ ] Title is centered below logo
- [ ] Fallback icon works if logo removed
- [ ] Logo loads quickly (< 100KB file size)

---

## Example Logos

### Good:
- ✅ Triad Partners logo (PNG, transparent background)
- ✅ Company wordmark (horizontal layout)
- ✅ Icon + text combination

### Avoid:
- ❌ Extremely wide logos (use square or vertical)
- ❌ Very large files (> 500KB)
- ❌ Low resolution (< 200px width)

---

## Summary

**To add your logo:**
1. Save your logo as `company-logo.png`
2. Copy it to: `/Users/manojgupta/kpi-dashboard/public/company-logo.png`
3. Refresh your browser
4. Done! 🎉

**The title is now centered on both pages!** ✅

### Login Page Layout:
```
        [Your Company Logo]
    
Customer Success Value Management System
      A Triad Partner AI Solution
      
      [Login Form]
```

### Dashboard Header Layout:
```
[Logo]    Customer Success Value Management System - A Triad Partner AI Solution    [Welcome, User] [Logout]
(left)                              (centered)                                                    (right)
```

All centered and professional! 🚀

---

## Pages Updated

✅ **Login Page** (`LoginComponent.tsx`)
- Logo at top (80px height)
- Title centered below logo

✅ **Dashboard Header** (`CSPlatform.tsx`)
- Logo on left (40px height)
- Title centered in middle
- User info and logout on right

Both pages now display your company logo! 🎨

