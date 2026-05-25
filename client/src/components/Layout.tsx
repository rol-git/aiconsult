import type { ReactNode } from 'react';
import Header from './Header';
import Footer from './Footer';
import styles from './Layout.module.css';

interface Props {
  children: ReactNode;
  fullHeight?: boolean;
}

export function Layout({ children, fullHeight = false }: Props) {
  return (
    <div className={fullHeight ? styles.shellFixed : styles.shell}>
      <a className="skip-link" href="#main">Перейти к содержимому</a>
      <Header />
      <main id="main" className={fullHeight ? styles.mainFull : styles.main}>
        {children}
      </main>
      {!fullHeight && <Footer />}
    </div>
  );
}

export default Layout;
