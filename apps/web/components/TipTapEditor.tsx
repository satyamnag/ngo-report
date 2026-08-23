"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import { TextStyle } from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";

type Editor = ReturnType<typeof useEditor> | null;

function ToolButton({
  editor,
  label,
  title,
  onClick,
  active,
}: {
  editor: Editor;
  label: string;
  title: string;
  onClick: () => void;
  active?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      className={active && editor?.isActive(active) ? "is-active" : ""}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

const Toolbar = ({ editor }: { editor: Editor }) => {
  if (!editor) return null;

  return (
    <div className="editor-toolbar">
      <select
        title="Heading level"
        style={{ width: "auto", padding: "4px 6px", marginRight: 6 }}
        value={
          editor.isActive("heading", { level: 1 })
            ? "1"
            : editor.isActive("heading", { level: 2 })
              ? "2"
              : editor.isActive("heading", { level: 3 })
                ? "3"
                : "0"
        }
        onChange={(e) => {
          const level = e.target.value;
          if (level === "0") {
            editor.chain().focus().setParagraph().run();
          } else {
            editor
              .chain()
              .focus()
              .toggleHeading({ level: Number(level) as 1 | 2 | 3 })
              .run();
          }
        }}
      >
        <option value="0">Paragraph</option>
        <option value="1">Heading 1</option>
        <option value="2">Heading 2</option>
        <option value="3">Heading 3</option>
      </select>

      <ToolButton
        editor={editor}
        label="B"
        title="Bold"
        active="bold"
        onClick={() => editor.chain().focus().toggleBold().run()}
      />
      <ToolButton
        editor={editor}
        label="I"
        title="Italic"
        active="italic"
        onClick={() => editor.chain().focus().toggleItalic().run()}
      />
      <ToolButton
        editor={editor}
        label="U"
        title="Underline"
        active="underline"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
      />
      <ToolButton
        editor={editor}
        label="S"
        title="Strikethrough"
        active="strike"
        onClick={() => editor.chain().focus().toggleStrike().run()}
      />
      <ToolButton
        editor={editor}
        label="• List"
        title="Bulleted list"
        active="bulletList"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      />
      <ToolButton
        editor={editor}
        label="1. List"
        title="Numbered list"
        active="orderedList"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      />
      <ToolButton
        editor={editor}
        label="❝"
        title="Quote"
        active="blockquote"
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      />
      <ToolButton
        editor={editor}
        label="⬅"
        title="Align left"
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
      />
      <ToolButton
        editor={editor}
        label="⏺"
        title="Align center"
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
      />
      <ToolButton
        editor={editor}
        label="➡"
        title="Align right"
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
      />
      <ToolButton
        editor={editor}
        label="⇔"
        title="Justify"
        onClick={() => editor.chain().focus().setTextAlign("justify").run()}
      />

      <label title="Text color" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        A
        <input
          type="color"
          style={{ width: 28, height: 28, padding: 0 }}
          onChange={(e) => editor.chain().focus().setColor(e.target.value).run()}
        />
      </label>
      <ToolButton
        editor={editor}
        label="▮"
        title="Highlight"
        active="highlight"
        onClick={() => editor.chain().focus().toggleHighlight({ color: "#fff3b0" }).run()}
      />
      <ToolButton
        editor={editor}
        label="⎯"
        title="Horizontal rule"
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
      />
      <span className="spacer" style={{ flex: 1 }} />
      <ToolButton
        editor={editor}
        label="↶"
        title="Undo"
        onClick={() => editor.chain().focus().undo().run()}
      />
      <ToolButton
        editor={editor}
        label="↷"
        title="Redo"
        onClick={() => editor.chain().focus().redo().run()}
      />
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
    extensions: [
      StarterKit,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
    ],
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