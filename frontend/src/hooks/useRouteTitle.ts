import { useLocation } from "react-router-dom";
import { useEffect } from "react";

/**
 * Sets a real, distinct <title> for every static route in one place,
 * instead of every page ever showing the same "Rockstar Organics" title
 * from index.html - previously true site-wide (see the SEO audit).
 *
 * Dynamic detail pages (a specific product, knowledge article, or
 * announcement) set their own more specific title once their data loads
 * via useDocumentTitle, which overrides whatever this sets for that
 * route on the next render - so this only needs static, pathname-only
 * entries here, not every possible URL.
 */
const TITLES: Record<string, string> = {
  "/": "Rockstar Organics — Agriculture. Trust. Transparency.",
  "/products": "Products | Rockstar Organics",
  "/dealers": "Dealer Locator | Rockstar Organics",
  "/farmer-support": "Farmer Support | Rockstar Organics",
  "/dealer-programme": "Become a Dealer | Rockstar Organics",
  "/distributors": "Distributors | Rockstar Organics",
  "/certificates": "Certificates & Documents | Rockstar Organics",
  "/gallery": "Agriculture Gallery | Rockstar Organics",
  "/knowledge": "Knowledge Center | Rockstar Organics",
  "/announcements": "News | Rockstar Organics",
  "/about": "About Rockstar Organics",
  "/leadership": "Leadership | Rockstar Organics",
  "/manufacturing": "Manufacturing | Rockstar Organics",
  "/research-and-development": "Research & Development | Rockstar Organics",
  "/quality-and-safety": "Quality & Safety | Rockstar Organics",
  "/sustainability": "Sustainability | Rockstar Organics",
  "/farmer-stories": "Farmer Stories | Rockstar Organics",
  "/careers": "Careers | Rockstar Organics",
  "/contact": "Contact | Rockstar Organics",
  "/legal/privacy": "Privacy Policy | Rockstar Organics",
  "/legal/terms": "Terms of Use | Rockstar Organics",
  "/legal/disclaimer": "Disclaimer | Rockstar Organics",
  "/legal/cookies": "Cookie Notice | Rockstar Organics",
  "/login": "Sign In | Rockstar Organics",
  "/signup": "Sign Up | Rockstar Organics",
  "/register": "Register | Rockstar Organics",
  "/forgot-password": "Forgot Password | Rockstar Organics",
};

export function useRouteTitle(): void {
  const location = useLocation();
  useEffect(() => {
    document.title = TITLES[location.pathname] || "Rockstar Organics";
  }, [location.pathname]);
}
