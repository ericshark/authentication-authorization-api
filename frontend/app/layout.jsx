import "./globals.css";
import { AppProviders } from "./providers";
import { AppShell } from "@/components/app-shell";

export const metadata = {
  title: "Aegis · Open Authentication Reference",
  description: "Documentation and live implementation reference for the FastAPI authentication platform.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
