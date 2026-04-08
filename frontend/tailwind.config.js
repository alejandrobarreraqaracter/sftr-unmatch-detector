/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			brand: {
  				orange: '#fc7c34',
  				navy: '#243444',
  				dark: '#000000',
  			}
  		}
  	}
  },
  plugins: [import("tailwindcss-animate")],
}

