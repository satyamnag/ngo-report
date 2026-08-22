"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

const Toolbar = ({ editor }: { editor: ReturnType<typeof useEditor> | null }) => {
  if (!editor) return null;
  const items: { label: string; onClick: () => void; active?: boolean }[] = [
    { label: "B", onClick: () => editor.chain().focus().toggleBold().run(), active: editor.isActive("bold") },
    { label: "I", onClick: () => editor.chain().focus().toggleItalic().run(), active: editor.isActive("italic") },
    { label: "S", onClick: () => editor.chain().focus().toggleStrike().run(), active: editor.isActive("strike") },
    { label: "U", onClick: () => editor.chain().focus().toggleUnderline().run(), active: editor.isActive("underline") },
    { label: "¶", onClick: () => editor.chain().focus().toggleBulletList().run(), active: editor.isActive("bulletList") },
    { label: "1.", onClick: () => editor.chain().focus().toggleOrderedList().run(), active: editor.isActive("orderedList") },
    { label: "❝", onClick: () => editor.chain().focus().toggleBlockquote().run(), active: editor.isActive("blockquote") },
  ];
  return (
    <div className="editor-toolbar">
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          className={item.active ? "is-active" : ""}
          onClick={item.onClick}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
};

export default function TipTapEditor({
  initialContent,
  onChange,
}: {
  initialContent: string;
  onChange: (html: string) => void;
}) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: initialContent || "<p></p>",
    immediatelyRender: false,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  });

  return (
    <div className="editor-shell">
      <Toolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}