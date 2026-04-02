"use client";

import { useState, useEffect } from "react";
import { getProducts, type ChillionProduct } from "@/lib/api/agents";

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL || "http://localhost:8000";

interface FullProduct {
  key: string;
  name: string;
  short_name: string;
  description: string;
  key_features: string[];
  pain_points: string[];
  blog_links: string[];
}

export default function ProductsManager() {
  const [products, setProducts] = useState<FullProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingProduct, setEditingProduct] = useState<FullProduct | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newProduct, setNewProduct] = useState<Partial<FullProduct>>({
    key: "",
    name: "",
    short_name: "",
    description: "",
    key_features: [],
    pain_points: [],
    blog_links: [],
  });

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/settings/products`);
      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      } else {
        // Fallback to basic products list
        const basicProducts = await getProducts();
        setProducts(basicProducts.map(p => ({
          key: p.key,
          name: p.name,
          short_name: p.short_name,
          description: p.description,
          key_features: [],
          pain_points: [],
          blog_links: [],
        })));
      }
    } catch (e) {
      console.error(e);
      // Fallback
      const basicProducts = await getProducts();
      setProducts(basicProducts.map(p => ({
        key: p.key,
        name: p.name,
        short_name: p.short_name,
        description: p.description,
        key_features: [],
        pain_points: [],
        blog_links: [],
      })));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProduct = async (product: FullProduct) => {
    try {
      await fetch(`${AGENTS_API_URL}/api/v1/settings/products/${product.key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(product),
      });
      
      setSuccess("Product saved!");
      setTimeout(() => setSuccess(null), 2000);
      setEditingProduct(null);
      await loadProducts();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAddProduct = async () => {
    if (!newProduct.name || !newProduct.key) {
      setError("Name and key are required");
      return;
    }
    
    try {
      await fetch(`${AGENTS_API_URL}/api/v1/settings/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newProduct),
      });
      
      setSuccess("Product added!");
      setTimeout(() => setSuccess(null), 2000);
      setShowAddModal(false);
      setNewProduct({
        key: "",
        name: "",
        short_name: "",
        description: "",
        key_features: [],
        pain_points: [],
        blog_links: [],
      });
      await loadProducts();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const productColors = [
    "from-violet-500 to-purple-500",
    "from-blue-500 to-indigo-500",
    "from-emerald-500 to-teal-500",
    "from-amber-500 to-orange-500",
    "from-pink-500 to-rose-500",
    "from-cyan-500 to-blue-500",
    "from-fuchsia-500 to-purple-500",
    "from-lime-500 to-green-500",
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-pink-400 to-rose-400 bg-clip-text text-transparent">
            Products
          </h1>
          <p className="text-zinc-400 mt-1">Manage Chillion products for outreach campaigns</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-pink-500 to-rose-500 text-white text-sm rounded-xl font-medium shadow-lg shadow-pink-500/25 hover:shadow-pink-500/40 transition"
        >
          ➕ Add Product
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}<button onClick={() => setError(null)} className="float-right">✕</button></div>}
      {success && <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">✓ {success}</div>}

      {/* Products Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {products.map((product, index) => (
          <div key={product.key} className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6 hover:border-pink-500/30 transition">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${productColors[index % productColors.length]} flex items-center justify-center text-2xl shadow-lg`}>
                  📦
                </div>
                <div>
                  <h3 className="font-semibold text-white">{product.name}</h3>
                  <p className="text-xs text-zinc-500">{product.short_name}</p>
                </div>
              </div>
              <button
                onClick={() => setEditingProduct(product)}
                className="px-3 py-1.5 text-xs bg-zinc-800 rounded-lg hover:bg-zinc-700 transition"
              >
                ✏️ Edit
              </button>
            </div>
            <p className="text-sm text-zinc-400 line-clamp-2">{product.description}</p>
            {product.key_features && product.key_features.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {product.key_features.slice(0, 3).map((f, i) => (
                  <span key={i} className="px-2 py-0.5 text-xs rounded-full bg-pink-500/10 text-pink-400 border border-pink-500/20">
                    {f.split(":")[0]}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit Modal */}
      {editingProduct && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">Edit Product</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Name</label>
                  <input
                    value={editingProduct.name}
                    onChange={e => setEditingProduct({ ...editingProduct, name: e.target.value })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Short Name</label>
                  <input
                    value={editingProduct.short_name}
                    onChange={e => setEditingProduct({ ...editingProduct, short_name: e.target.value })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Description</label>
                <textarea
                  value={editingProduct.description}
                  onChange={e => setEditingProduct({ ...editingProduct, description: e.target.value })}
                  rows={3}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none resize-none"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Key Features (one per line)</label>
                <textarea
                  value={editingProduct.key_features?.join("\n") || ""}
                  onChange={e => setEditingProduct({ ...editingProduct, key_features: e.target.value.split("\n").filter(Boolean) })}
                  rows={4}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none resize-none font-mono text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Pain Points (one per line)</label>
                <textarea
                  value={editingProduct.pain_points?.join("\n") || ""}
                  onChange={e => setEditingProduct({ ...editingProduct, pain_points: e.target.value.split("\n").filter(Boolean) })}
                  rows={4}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none resize-none font-mono text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Blog Links (one per line)</label>
                <textarea
                  value={editingProduct.blog_links?.join("\n") || ""}
                  onChange={e => setEditingProduct({ ...editingProduct, blog_links: e.target.value.split("\n").filter(Boolean) })}
                  rows={2}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none resize-none font-mono text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setEditingProduct(null)} className="px-4 py-2 bg-zinc-800 rounded-lg text-sm">Cancel</button>
              <button onClick={() => handleSaveProduct(editingProduct)} className="px-4 py-2 bg-gradient-to-r from-pink-500 to-rose-500 text-white rounded-lg text-sm font-medium">Save Product</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">Add New Product</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Key (unique identifier)</label>
                  <input
                    value={newProduct.key}
                    onChange={e => setNewProduct({ ...newProduct, key: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none"
                    placeholder="my_product"
                  />
                </div>
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Short Name</label>
                  <input
                    value={newProduct.short_name}
                    onChange={e => setNewProduct({ ...newProduct, short_name: e.target.value })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Name</label>
                <input
                  value={newProduct.name}
                  onChange={e => setNewProduct({ ...newProduct, name: e.target.value })}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Description</label>
                <textarea
                  value={newProduct.description}
                  onChange={e => setNewProduct({ ...newProduct, description: e.target.value })}
                  rows={3}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-pink-500 focus:outline-none resize-none"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowAddModal(false)} className="px-4 py-2 bg-zinc-800 rounded-lg text-sm">Cancel</button>
              <button onClick={handleAddProduct} className="px-4 py-2 bg-gradient-to-r from-pink-500 to-rose-500 text-white rounded-lg text-sm font-medium">Add Product</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

