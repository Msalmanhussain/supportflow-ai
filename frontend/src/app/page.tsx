import OrderLookupForm from "@/components/OrderLookupForm";
import SiteNav from "@/components/SiteNav";
import SupportDraftForm from "@/components/SupportDraftForm";

import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <SiteNav />
        <h1 className={styles.brand}>SupportFlow AI</h1>
        <p className={styles.lead}>
          Local portfolio demo: synthetic order lookup and review-only support
          drafts. The model classifies messages; application code retrieves
          facts and templates the reply. Generated drafts are saved for local
          human review. Nothing is sent.
        </p>
        <div className={styles.sections}>
          <OrderLookupForm />
          <SupportDraftForm />
        </div>
      </main>
    </div>
  );
}
