import React from 'react'
import rehypeRaw from 'rehype-raw'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { isAllowedImage } from './markdown-images'

interface MarkdownRendererProps {
    content: string,
    className?: string,
    allowHtml?: boolean,
    imageOrigins?: string[]
}

/**
 * Tailwind's reset leaves bare <table>/<pre> unstyled. A table goes in the `.tableWrapper` the message styles expect (rich-text.css), so a
 * wide one scrolls instead of stretching the page; a code block gets the same well as an inline code span.
 */
const components: Components = {
    table: ({ children }) => <div className="tableWrapper"><table>{children}</table></div>,
    pre: ({ children }) => <pre className="my-2 overflow-x-auto rounded-md bg-surface-gray-2 p-3 text-sm">{children}</pre>,
    a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
}

/** A picture opens full size in a new tab; one from an origin we do not expect is shown as its text, never loaded. */
const picture = (origins: string[]): Components["img"] => ({ src, alt }) =>
    isAllowedImage(typeof src === 'string' ? src : undefined, origins)
        ? <a href={src as string} target="_blank" rel="noreferrer" className="block w-fit max-w-full">
            <img src={src as string} alt={alt ?? ''} loading="lazy" className="my-1 max-h-112 max-w-full rounded-md border border-outline-gray-2" />
        </a>
        : <span className="text-ink-gray-5">{alt}</span>

/**
 * The real renderer. Loaded lazily by markdown.tsx — import THAT, not this. `className` styles the whole block (e.g. "tiptap" for
 * message styling); `allowHtml={false}` shows raw HTML as text; `imageOrigins` limits where pictures load from.
 */
const MarkdownImpl: React.FC<MarkdownRendererProps> = ({ content, className, allowHtml = true, imageOrigins }) => {
    const markdown = (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={allowHtml ? [rehypeRaw] : []}
            components={imageOrigins ? { ...components, img: picture(imageOrigins) } : components}
        >
            {content}
        </ReactMarkdown>
    )
    return className ? <div className={className}>{markdown}</div> : markdown
}

export default MarkdownImpl
