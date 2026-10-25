import Link from "next/link";

import styles from "./SiteNav.module.css";

export default function SiteNav() {
  return (
    <nav className={styles.nav} aria-label="Primary">
      <Link href="/" className={styles.brandLink}>
        SupportFlow AI
      </Link>
      <ul className={styles.links}>
        <li>
          <Link href="/">Generate draft</Link>
        </li>
        <li>
          <Link href="/requests">Review queue</Link>
        </li>
      </ul>
    </nav>
  );
}
