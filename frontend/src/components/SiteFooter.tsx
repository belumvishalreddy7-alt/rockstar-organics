export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <h4>Rockstar Organics</h4>
            <p className="small muted">Agriculture. Trust. Transparency.</p>
            <p className="small muted">
              An agricultural enterprise rooted in Telangana, India, serving the farming community across
              Ranga Reddy district and beyond.
            </p>
          </div>
          <div>
            <h4>Website</h4>
            <ul>
              <li><a href="/">Home</a></li>
              <li><a href="/about">About Rockstar Organics</a></li>
              <li><a href="/products">Products</a></li>
              <li><a href="/dealers">Dealers</a></li>
              <li><a href="/distributors">Distributors</a></li>
              <li><a href="/contact">Contact</a></li>
              <li><a href="/login">Login</a></li>
            </ul>
          </div>
          <div>
            <h4>Platform</h4>
            <ul>
              <li><a href="/login">Farmer Login</a></li>
              <li><a href="/login">Dealer Login</a></li>
              <li><a href="/login">Distributor Login</a></li>
              <li><a href="/login">Field Officer Login</a></li>
              <li><a href="/login">Admin Login</a></li>
            </ul>
          </div>
          <div>
            <h4>Legal</h4>
            <ul>
              <li><a href="/legal/privacy">Privacy Policy</a></li>
              <li><a href="/legal/terms">Terms of Use</a></li>
              <li><a href="/legal/disclaimer">Disclaimer</a></li>
            </ul>
          </div>
        </div>
        <p className="small">&copy; Rockstar Organics. All rights reserved.</p>
      </div>
    </footer>
  );
}
