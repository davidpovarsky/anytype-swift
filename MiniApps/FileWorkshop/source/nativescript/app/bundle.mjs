import { Page, ScrollView, StackLayout, Label, TextField, TextView, Button, Device } from '@nativescript/core';
import { registerWindowFactory } from '@hanlin/window-factory';

// Every window owns its actual provider-bound services and editable state.
registerWindowFactory(({ id, packageID, services }) => {
  const rtl = /^(he|iw)([-_]|$)/i.test(String(Device.language || 'en'));
  const words = rtl ? {
    title: 'סדנת קבצים', help: 'בחירת קובץ קיים, או יצירת קובץ טקסט חדש. הקובץ יוחזר רק בלחיצה על הכפתור.',
    loading: 'טוען את הבקשה…', name: 'שם הקובץ', new: 'קובץ טקסט חדש',
    returning: 'שומר ומחזיר…', returned: 'הקובץ הוחזר', cancel: 'ביטול',
    cancelled: 'הבקשה בוטלה', send: 'החזרת הקובץ', ready: 'מוכן',
    text: 'אפשר לערוך טקסט UTF-8. המקור יישמר באפליקציה שממנה נשלח.',
    binary: 'קובץ בינארי: ניתן לשנות שם ולהחזיר את הבתים המקוריים.',
    create: 'קובץ טקסט חדש מתוכן המקור', noContext: 'פתחו את סדנת הקבצים מתפריט MiniApps במסמך או בהערה.',
    invalidName: 'יש להזין שם קובץ תקין ללא מפרידי נתיב.', noData: 'לא ניתן לקרוא את הקובץ.',
    choose: 'בחרו קובץ או צרו קובץ חדש', source: 'מקור', bytes: 'בתים',
  } : {
    title: 'File Workshop', help: 'Choose an existing file or create a text file. Nothing is returned until you choose Return file.',
    loading: 'Loading request…', name: 'File name', new: 'New text file',
    returning: 'Saving and returning…', returned: 'File returned', cancel: 'Cancel',
    cancelled: 'Request cancelled', send: 'Return file', ready: 'Ready',
    text: 'Edit UTF-8 text. The source app keeps the original attachment.',
    binary: 'Binary file: rename it and return its original bytes.',
    create: 'New text file from the source content', noContext: 'Open File Workshop from a document or note’s MiniApps menu.',
    invalidName: 'Enter a valid file name without path separators.', noData: 'The file could not be read.',
    choose: 'Choose a file or create a new one', source: 'Source', bytes: 'bytes',
  };
  const page = new Page();
  page.actionBarHidden = true;
  const scroll = new ScrollView();
  const layout = new StackLayout();
  layout.padding = 20;
  scroll.content = layout;
  page.content = scroll;
  const controls = [];
  const label = (text, identifier, size = 16) => {
    const view = new Label();
    view.text = text;
    view.textWrap = true;
    view.fontSize = size;
    view.marginBottom = 12;
    view.textAlignment = rtl ? 'right' : 'left';
    view.accessibilityIdentifier = identifier;
    layout.addChild(view);
    return view;
  };
  const button = (title, identifier, action) => {
    const view = new Button();
    view.text = title;
    view.accessibilityIdentifier = identifier;
    view.marginBottom = 10;
    view.on('tap', () => { void Promise.resolve().then(action).catch(showError); });
    controls.push(view);
    return view;
  };
  label(words.title, 'fileworkshop.title', 26);
  label(words.help, 'fileworkshop.help');
  const sourceTitle = label('', 'fileworkshop.source-title');
  const filesLayout = new StackLayout();
  layout.addChild(filesLayout);
  const create = button(words.new, 'fileworkshop.new', newTextFile);
  layout.addChild(create);
  const fileInfo = label('', 'fileworkshop.file-info');
  label(words.name, 'fileworkshop.filename-label');
  const fileName = new TextField();
  fileName.accessibilityIdentifier = 'fileworkshop.filename';
  fileName.hint = 'document.txt';
  fileName.autocorrect = false;
  fileName.autocapitalizationType = 'none';
  fileName.textAlignment = rtl ? 'right' : 'left';
  fileName.marginBottom = 12;
  layout.addChild(fileName);
  const mode = label('', 'fileworkshop.mode');
  const editor = new TextView();
  editor.accessibilityIdentifier = 'fileworkshop.editor';
  editor.height = 220;
  editor.autocorrect = false;
  editor.autocapitalizationType = 'none';
  editor.textAlignment = rtl ? 'right' : 'left';
  editor.marginBottom = 12;
  layout.addChild(editor);
  const status = label(words.loading, 'fileworkshop.status');
  const send = button(words.send, 'fileworkshop.return', returnFile);
  const cancel = button(words.cancel, 'fileworkshop.cancel', cancelRequest);
  layout.addChild(send);
  layout.addChild(cancel);
  let context;
  let current;
  let phase = 'loading';
  let epoch = 0;
  let prepared;
  function setPhase(value, message) {
    phase = value;
    if (message !== undefined) status.text = message;
    const editable = value === 'ready';
    for (const control of controls) control.isEnabled = editable;
    create.isEnabled = !!context && editable;
    send.isEnabled = editable && !!current;
    cancel.isEnabled = !!context && (editable || value === 'failed');
    fileName.isEnabled = editable && !!current;
    editor.isEditable = editable && !!current?.editable;
  }
  function showError(error) {
    setPhase(context ? 'ready' : 'failed', String(error?.message ?? error));
  }
  function dataFromBase64(value) {
    const data = NSData.alloc().initWithBase64EncodedStringOptions(value, 0);
    if (data == null) throw new Error(words.noData);
    return data;
  }
  function textData(value) {
    const data = NSString.alloc().initWithString(value).dataUsingEncoding(NSUTF8StringEncoding);
    if (data == null) throw new Error(words.noData);
    return data;
  }
  function utf8Text(data) {
    const value = NSString.alloc().initWithDataEncoding(data, NSUTF8StringEncoding);
    return value == null ? null : String(value);
  }
  function editableType(item) {
    return ['public.plain-text', 'public.utf8-plain-text', 'public.text',
      'public.json', 'public.xml', 'public.source-code', 'net.daringfireball.markdown']
      .includes(item.typeIdentifier) ||
      /\.(txt|md|json|csv|tsv|xml|html|css|js|mjs|ts|swift|py|yaml|yml|log)$/i.test(item.name || '');
  }
  async function selectFile(item) {
    if (phase !== 'ready') return;
    const generation = ++epoch;
    setPhase('loading', words.loading);
    const response = await services.miniapps.readAttachment(item.attachmentID);
    if (generation !== epoch) return;
    const data = dataFromBase64(response.base64);
    const decoded = editableType(item) ? utf8Text(data) : null;
    current = { item, base64: response.base64, originalText: decoded,
      editable: decoded !== null, bytes: Number(data.length) };
    prepared = undefined;
    fileName.text = item.name || 'attachment';
    editor.text = decoded ?? '';
    mode.text = current.editable ? words.text : words.binary;
    fileInfo.text = String(current.bytes) + ' ' + words.bytes;
    setPhase('ready', words.ready);
  }
  function newTextFile() {
    if (!context || phase !== 'ready') return;
    ++epoch;
    const text = context.inputs.filter(item => item.kind === 'text')
      .map(item => item.text || '').join('\n') || context.source.selection?.text || context.source.documentText || '';
    current = { item: undefined, base64: undefined, originalText: undefined, editable: true, bytes: 0 };
    prepared = undefined;
    fileName.text = 'document.txt';
    editor.text = text;
    mode.text = words.text;
    fileInfo.text = words.create;
    setPhase('ready', words.ready);
  }
  async function returnFile() {
    if (!context || phase !== 'ready' || !current) return;
    fileName.dismissSoftInput();
    editor.dismissSoftInput();
    const name = String(fileName.text || '').trim();
    if (!name || name === '.' || name === '..' || /[\/\\\u0000]/.test(name) ||
        Number(textData(name).length) > 255) throw new Error(words.invalidName);
    const original = current;
    const text = String(editor.text || '');
    const changedText = original.editable && (original.base64 === undefined || text !== original.originalText);
    const data = changedText ? textData(text) : dataFromBase64(original.base64);
    const base64 = changedText ? String(data.base64EncodedStringWithOptions(0)) : original.base64;
    const typeIdentifier = changedText && !original.item
      ? 'public.utf8-plain-text' : (original.item?.typeIdentifier || 'public.data');
    const key = JSON.stringify([name, typeIdentifier, base64]);
    setPhase('returning', words.returning);
    try {
      if (!prepared || prepared.key !== key) {
        const item = await services.miniapps.writeAttachment({ base64, name, typeIdentifier });
        prepared = { key, item };
      }
      await services.miniapps.complete({
        operation: 'insert', items: [prepared.item],
        metadata: { packageID, packageVersion: '1.0.0', windowSessionID: id,
          sourceAppID: context.source.appID, documentID: context.source.documentID || '',
          sourceAttachmentID: original.item?.attachmentID || '',
          sourceBytes: String(original.bytes), outputBytes: String(data.length),
          fileMode: original.item ? (changedText ? 'edited-utf8' : 'original-bytes') : 'new-utf8' },
      });
      ++epoch;
      setPhase('returned', words.returned);
    } catch (error) { showError(error); }
  }
  async function cancelRequest() {
    if (!context || (phase !== 'ready' && phase !== 'failed')) return;
    ++epoch;
    setPhase('cancelling', words.cancel);
    try { await services.miniapps.cancel(); setPhase('cancelled', words.cancelled); }
    catch (error) { showError(error); }
  }
  page.on('loaded', () => {
    page.nativeViewProtected.semanticContentAttribute = rtl
      ? UISemanticContentAttribute.ForceRightToLeft : UISemanticContentAttribute.ForceLeftToRight;
  });
  setPhase('loading', words.loading);
  services.miniapps.getContext().then(async value => {
    context = value;
    sourceTitle.text = words.source + ': ' +
      (value.source.documentTitle || value.source.displayName || value.source.appID);
    const files = value.inputs.filter(item => item.kind === 'file' && item.attachmentID);
    for (const item of files) {
      const pick = button(item.name || item.attachmentID,
        'fileworkshop.source-' + item.attachmentID, () => selectFile(item));
      filesLayout.addChild(pick);
    }
    setPhase('ready', words.choose);
    if (files.length > 0) await selectFile(files[0]);
    else newTextFile();
  }).catch(error => {
    setPhase('failed', words.noContext + '\n' + String(error?.message ?? error));
  });
  return page;
});
