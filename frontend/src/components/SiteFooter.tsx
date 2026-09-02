import { useLanguage } from "../context/LanguageContext";

export function SiteFooter() {
  const { t } = useLanguage();
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <h4>Rockstar Organics</h4>
            <p className="small muted">{t("footer.tagline")}</p>
            <p className="small muted">{t("footer.about")}</p>
          </div>
          <div>
            <h4>{t("footer.company")}</h4>
            <ul>
              <li><a href="/about">{t("footer.aboutLink")}</a></li>
              <li><a href="/leadership">{t("footer.leadership")}</a></li>
              <li><a href="/manufacturing">{t("footer.manufacturing")}</a></li>
              <li><a href="/research-and-development">{t("footer.rnd")}</a></li>
              <li><a href="/quality-and-safety">{t("footer.qualitySafety")}</a></li>
              <li><a href="/sustainability">{t("footer.sustainability")}</a></li>
              <li><a href="/careers">{t("footer.careers")}</a></li>
            </ul>
          </div>
          <div>
            <h4>{t("footer.website")}</h4>
            <ul>
              <li><a href="/">{t("nav.home")}</a></li>
              <li><a href="/products">{t("nav.products")}</a></li>
              <li><a href="/knowledge">{t("footer.knowledgeCenter")}</a></li>
              <li><a href="/farmer-stories">{t("footer.farmerStories")}</a></li>
              <li><a href="/announcements">{t("footer.news")}</a></li>
              <li><a href="/dealers">{t("footer.dealerLocator")}</a></li>
              <li><a href="/distributors">{t("nav.distributors")}</a></li>
              <li><a href="/farmer-support">{t("footer.farmerSupport")}</a></li>
              <li><a href="/contact">{t("nav.contact")}</a></li>
            </ul>
          </div>
          <div>
            <h4>{t("footer.platform")}</h4>
            <ul>
              <li><a href="/login">{t("footer.farmerLogin")}</a></li>
              <li><a href="/login">{t("footer.dealerLogin")}</a></li>
              <li><a href="/login">{t("footer.distributorLogin")}</a></li>
              <li><a href="/login">{t("footer.fieldOfficerLogin")}</a></li>
              <li><a href="/login">{t("footer.adminLogin")}</a></li>
            </ul>
          </div>
          <div>
            <h4>{t("footer.legal")}</h4>
            <ul>
              <li><a href="/legal/privacy">{t("footer.privacyPolicy")}</a></li>
              <li><a href="/legal/terms">{t("footer.termsOfUse")}</a></li>
              <li><a href="/legal/disclaimer">{t("footer.disclaimer")}</a></li>
            </ul>
          </div>
        </div>
        <p className="small">{t("footer.rightsReserved")}</p>
      </div>
    </footer>
  );
}
