SCORM PLAYER react+js
Структура проекта
```
scorm-player/
├── public/
│   └── index.html
├── src/
│   ├── utils/
│   │   ├── scormEmulator.js
│   │   └── parseManifest.js
│   ├── components/
│   │   └── SCORMPlayer.js
│   └── App.js
│   └── index.js
├── package.json
```

### Установка зависимостей

```
npx create-react-app scorm-player --template javascript
cd scorm-player
npm install jszip
```
Не устанавливайте @types/* — мы используем чистый JS.


### src/utils/scormEmulator.js (Эмулирует SCORM API для iframe.)

```
// src/utils/scormEmulator.js

export class SCOManager {
  constructor() {
    this.data = {};
    this.initialized = false;
  }

  // === SCORM 1.2 ===
  LMSInitialize() {
    console.log('SCORM 1.2: LMSInitialize');
    this.initialized = true;
    return 'true';
  }

  LMSFinish() {
    console.log('SCORM 1.2: LMSFinish');
    this.initialized = false;
    return 'true';
  }

  LMSGetValue(key) {
    if (!this.initialized) return '';
    const value = this.data[key] || '';
    console.log('SCORM 1.2: GetValue', key, '=>', value);
    return value;
  }

  LMSSetValue(key, value) {
    if (!this.initialized) return 'false';
    console.log('SCORM 1.2: SetValue', key, '=', value);
    this.data[key] = String(value);
    return 'true';
  }

  LMSCommit() {
    console.log('SCORM 1.2: LMSCommit');
    return 'true';
  }

  LMSGetLastError() { return '0'; }
  LMSGetErrorString() { return 'No error'; }
  LMSGetDiagnostic() { return ''; }

  // === SCORM 2004 ===
  Initialize() { return this.LMSInitialize(); }
  Terminate() { return this.LMSFinish(); }
  GetValue(key) { return this.LMSGetValue(key); }
  SetValue(key, value) { return this.LMSSetValue(key, value); }
  Commit() { return this.LMSCommit(); }
  GetLastError() { return this.LMSGetLastError(); }
  GetErrorString() { return this.LMSGetErrorString(); }
  GetDiagnostic() { return this.LMSGetDiagnostic(); }

  // Утилиты
  getData() {
    return { ...this.data };
  }

  reset() {
    this.data = {};
    this.initialized = false;
  }
}

export const injectSCORMAPI = (windowRef, scoManager) => {
  // SCORM 1.2
  windowRef.API = {
    LMSInitialize: scoManager.LMSInitialize.bind(scoManager),
    LMSFinish: scoManager.LMSFinish.bind(scoManager),
    LMSGetValue: scoManager.LMSGetValue.bind(scoManager),
    LMSSetValue: scoManager.LMSSetValue.bind(scoManager),
    LMSCommit: scoManager.LMSCommit.bind(scoManager),
    LMSGetLastError: scoManager.LMSGetLastError.bind(scoManager),
    LMSGetErrorString: scoManager.LMSGetErrorString.bind(scoManager),
    LMSGetDiagnostic: scoManager.LMSGetDiagnostic.bind(scoManager),
  };

  // SCORM 2004
  windowRef.API_1484_11 = {
    Initialize: scoManager.Initialize.bind(scoManager),
    Terminate: scoManager.Terminate.bind(scoManager),
    GetValue: scoManager.GetValue.bind(scoManager),
    SetValue: scoManager.SetValue.bind(scoManager),
    Commit: scoManager.Commit.bind(scoManager),
    GetLastError: scoManager.GetLastError.bind(scoManager),
    GetErrorString: scoManager.GetErrorString.bind(scoManager),
    GetDiagnostic: scoManager.GetDiagnostic.bind(scoManager),
  };
};
```
### src/utils/parseManifest.js(Парсит imsmanifest.xml.)
```
// src/utils/parseManifest.js

export const parseManifest = (xmlText) => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
  const items = [];

  const parseItem = (el) => {
    const id = el.getAttribute('identifier') || '';
    const titleEl = el.querySelector('title');
    const title = titleEl?.textContent || 'Без названия';
    const itemRef = el.getAttribute('identifierref');

    let href = '';
    if (itemRef) {
      const resource = xmlDoc.querySelector(`resource[identifier="${itemRef}"]`);
      href = resource?.getAttribute('href') || '';
    }

    const children = [];
    const childItems = el.querySelectorAll('item');
    childItems.forEach((child) => {
      if (child.parentElement === el) {
        children.push(parseItem(child));
      }
    });

    return { id, title, href, children };
  };

  const organization = xmlDoc.querySelector('organization');
  if (organization) {
    const topLevelItems = organization.querySelectorAll('item');
    topLevelItems.forEach((item) => {
      if (item.parentElement === organization) {
        items.push(parseItem(item));
      }
    });
  }

  return items;
};
```
### src/components/SCORMPlayer.js(Основной компонент плеера)
```
// src/components/SCORMPlayer.js
import React, { useState, useRef, useEffect } from 'react';
import JSZip from 'jszip';
import { parseManifest } from '../utils/parseManifest';
import { SCOManager, injectSCORMAPI } from '../utils/scormEmulator';

const SCORMPlayer = () => {
  const [manifest, setManifest] = useState([]);
  const [currentUrl, setCurrentUrl] = useState('');
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);
  const scoManagerRef = useRef(new SCOManager());
  const fileUrlsRef = useRef({});

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setError(null);
      const zip = await JSZip.loadAsync(file);
      const manifestFile = zip.file('imsmanifest.xml');
      if (!manifestFile) {
        throw new Error('Файл imsmanifest.xml не найден');
      }

      const manifestText = await manifestFile.async('text');
      const items = parseManifest(manifestText);
      setManifest(items);

      // Создаём URL для каждого файла
      const fileUrls = {};
      zip.forEach((relativePath, zipEntry) => {
        if (!zipEntry.dir) {
          zipEntry.async('blob').then((blob) => {
            fileUrls[relativePath] = URL.createObjectURL(blob);
          });
        }
      });

      // Ждём, пока все blob-URL создадутся (упрощённо — через таймаут)
      setTimeout(() => {
        fileUrlsRef.current = fileUrls;
        if (items.length > 0 && items[0].href) {
          loadItem(items[0]);
        }
      }, 100);
    } catch (err) {
      setError(err.message || 'Ошибка при загрузке пакета');
    }
  };

  const loadItem = (item) => {
    if (item.href && fileUrlsRef.current[item.href]) {
      setCurrentUrl(fileUrlsRef.current[item.href]);
    } else {
      setCurrentUrl('');
    }
  };

  const renderTOC = (items, level = 0) => (
    <ul style={{ paddingLeft: level * 20, listStyle: 'none', margin: 0, padding: 0 }}>
      {items.map((item) => (
        <li key={item.id} style={{ marginBottom: '4px' }}>
          <button
            onClick={() => loadItem(item)}
            disabled={!item.href}
            style={{
              width: '100%',
              textAlign: 'left',
              padding: '6px 10px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: item.href ? 'pointer' : 'not-allowed',
            }}
          >
            {item.title}
          </button>
          {item.children && renderTOC(item.children, level + 1)}
        </li>
      ))}
    </ul>
  );

  // Инжектим SCORM API в iframe при смене URL
  useEffect(() => {
    if (iframeRef.current && currentUrl) {
      const iframe = iframeRef.current;
      const iframeWindow = iframe.contentWindow;
      if (iframeWindow) {
        scoManagerRef.current.reset();
        injectSCORMAPI(iframeWindow, scoManagerRef.current);
      }
    }
  }, [currentUrl]);

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '300px', padding: '15px', background: '#f8f9fa', borderRight: '1px solid #dee2e6' }}>
        <h3>SCORM Player</h3>
        <input type="file" accept=".zip" onChange={handleFileUpload} style={{ marginBottom: '15px' }} />
        {error && <div style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}
        {manifest.length > 0 && (
          <>
            <h4>Содержание:</h4>
            {renderTOC(manifest)}
          </>
        )}
        <details style={{ marginTop: '20px' }}>
          <summary>Данные SCORM</summary>
          <pre style={{ fontSize: '12px', backgroundColor: '#fff', padding: '8px', borderRadius: '4px' }}>
            {JSON.stringify(scoManagerRef.current.getData(), null, 2)}
          </pre>
        </details>
      </div>

      <div style={{ flex: 1 }}>
        {currentUrl ? (
          <iframe
            ref={iframeRef}
            src={currentUrl}
            title="SCORM Content"
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            Загрузите SCORM-пакет (.zip)
          </div>
        )}
      </div>
    </div>
  );
};

export default SCORMPlayer;
```
### src/App.js
```
// src/App.js
import React from 'react';
import SCORMPlayer from './components/SCORMPlayer';
import './App.css';

function App() {
  return (
    <div className="App">
      <SCORMPlayer />
    </div>
  );
}

export default App;

```
### src/index.js
```
// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```
### Запуск
```
npm start
```
### Возможности

Поддержка SCORM 1.2 и SCORM 2004  
Отображение структуры курса  
Сохранение прогресса в памяти (можно доработать под localStorage)  
Отладка данных SCORM в реальном времени

###  Важно
Некоторые курсы используют относительные пути — убедитесь, что структура ZIP корректна.
iframe загружается из blob: URL — это ограничивает доступ к внешним ресурсам (CORS).
Для продакшена можно добавить экспорт данных, сохранение сессии и т.д.


