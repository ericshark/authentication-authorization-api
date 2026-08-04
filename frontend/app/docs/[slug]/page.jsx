import { notFound } from "next/navigation";
import { DocsArticle } from "@/components/docs/docs-article";
import { docs, docsOrder } from "@/lib/docs";

export function generateStaticParams() {
  return docsOrder.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const doc = docs[slug];
  if (!doc) return {};
  return { title: `${doc.title} · Aegis Docs`, description: doc.description };
}

export default async function DocumentationPage({ params }) {
  const { slug } = await params;
  const doc = docs[slug];
  if (!doc) notFound();
  return <DocsArticle doc={doc} slug={slug} />;
}
