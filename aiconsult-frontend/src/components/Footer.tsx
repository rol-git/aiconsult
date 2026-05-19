import styles from './Footer.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.row}`}>
        <span>© {new Date().getFullYear()} ЧС-Консультант. Тюменская область.</span>
        <span className="muted small">
          Информация ИИ носит справочный характер. В экстренных случаях звоните 112.
        </span>
      </div>
    </footer>
  );
}

export default Footer;
