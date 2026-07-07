import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PS5 Hunter - Real-time Indian Retailer Stock Monitor",
  description: "Eliminate manual refreshes. Get instant Telegram, Discord, and email alerts the split-second a PlayStation 5 becomes available at Indian stores.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
