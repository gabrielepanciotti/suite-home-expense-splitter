import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import {
  AppShell,
  Button,
  EmptyState,
  PersonalizzaVista,
  Spinner,
  VistaProvider,
  useVista,
  type VistaFetcher,
} from "@suite/design-system";
import { LanguageSwitcher, useLanguage } from "@suite/i18n";
import {
  AlertIcon,
  DownloadIcon,
  InboxIcon,
  ListIcon,
  ScaleIcon,
  SlidersIcon,
} from "./components/icons";
import { useCompactViewport } from "./hooks/useCompactViewport";
import { Esporta } from "./pages/Esporta";
import { Saldo } from "./pages/Saldo";
import { Spese } from "./pages/Spese";

const PAGES: Record<string, ComponentType> = {
  saldo: Saldo,
  spese: Spese,
  esporta: Esporta,
};

const SECTION_ICONS: Record<string, ReactNode> = {
  saldo: <ScaleIcon />,
  spese: <ListIcon />,
  esporta: <DownloadIcon />,
};

function StatusShell({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      <AppShell.Content className="grid place-items-center p-4 sm:p-6">
        {children}
      </AppShell.Content>
    </AppShell>
  );
}

function HomeExpenseSplitterShell() {
  const { t } = useLanguage();
  const { sezioniVisibili, stato, etichetta, ricarica } = useVista();
  const [section, setSection] = useState(() => window.location.hash.slice(1));
  const compact = useCompactViewport();

  useEffect(() => {
    const sync = () => setSection(window.location.hash.slice(1));
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const items = sezioniVisibili.slice(0, 7);
  const active = items.some((item) => item.id === section)
    ? section
    : items[0]?.id;

  useEffect(() => {
    if (active && window.location.hash !== `#${active}`) {
      window.location.hash = active;
    }
  }, [active]);

  if (stato === "loading") {
    return (
      <StatusShell>
        <EmptyState
          role="status"
          icon={<Spinner />}
          title={t("common.loading")}
          glow={false}
        />
      </StatusShell>
    );
  }

  if (stato === "error") {
    return (
      <StatusShell>
        <EmptyState
          icon={<AlertIcon />}
          title={t("vista.errorTitle")}
          description={t("vista.errorDescription")}
          glow={false}
          action={
            <Button className="min-h-11" onClick={() => void ricarica()}>
              {t("common.retry")}
            </Button>
          }
        />
      </StatusShell>
    );
  }

  const Page = active ? PAGES[active] : undefined;
  return (
    <AppShell defaultCollapsed={compact}>
      {/* sotto `md` la barra è un overlay largo 48 px: senza togliere il padding laterale le voci restano da 31 px */}
      <AppShell.Sidebar className="max-md:px-0">
        {items.map((item) => (
          <AppShell.Sidebar.Item
            key={item.id}
            icon={SECTION_ICONS[item.id] ?? <ListIcon />}
            label={item.titolo}
            active={active === item.id}
            className="min-h-11"
            onClick={() => {
              window.location.hash = item.id;
            }}
          />
        ))}
      </AppShell.Sidebar>
      <div className="flex min-w-0 flex-1 flex-col max-md:pl-12">
        <AppShell.Topbar>
          <span className="hidden min-w-0 truncate text-sm font-medium text-text sm:block">
            {t("app.title")} <span className="text-muted">· {etichetta}</span>
          </span>
          <div className="ml-auto flex flex-none items-center gap-2">
            <LanguageSwitcher className="[&_button]:min-h-11 [&_button]:min-w-11" />
            <PersonalizzaVista
              trigger={
                <Button
                  variant="secondary"
                  className="min-h-11 min-w-11 px-2 sm:px-3"
                  aria-label={t("vista.customize")}
                  title={t("vista.customize")}
                >
                  <SlidersIcon className="size-4" />
                  <span className="hidden sm:inline">{t("vista.customize")}</span>
                </Button>
              }
            />
          </div>
        </AppShell.Topbar>
        <AppShell.Content className="p-3 sm:p-6">
          {Page ? (
            <Page />
          ) : (
            <EmptyState
              icon={<InboxIcon />}
              title={t("vista.emptyTitle")}
              description={t("vista.emptyDescription")}
              glow={false}
            />
          )}
        </AppShell.Content>
      </div>
    </AppShell>
  );
}

export function HomeExpenseSplitterApp({
  vistaFetcher,
}: {
  vistaFetcher?: VistaFetcher;
}) {
  return (
    <VistaProvider fetcher={vistaFetcher}>
      <HomeExpenseSplitterShell />
    </VistaProvider>
  );
}

export default function App({ vistaFetcher }: { vistaFetcher?: VistaFetcher }) {
  return <HomeExpenseSplitterApp vistaFetcher={vistaFetcher} />;
}
