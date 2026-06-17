import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, UserPlus, Users, Check, Search, X, Plus, Trash2 } from 'lucide-react'
import Button from '../../components/ui/Button'
import { toast } from 'sonner'
import { ordersApi, customersApi } from '../../api'

const EMPTY_PRODUCT = { product_name: '', quantity: '', unit: 'MT', notes: '' }

export default function CreateOrderPage() {
  const navigate = useNavigate()
  const dropdownRef = useRef(null)
  
  const [workflowMode, setWorkflowMode] = useState(null) // 'existing' | 'new' | null
  const [loading, setLoading] = useState(false)
  
  // Existing buyer list & search state
  const [customers, setCustomers] = useState([])
  const [loadingCustomers, setLoadingCustomers] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  // Form states
  const [existingBuyerForm, setExistingBuyerForm] = useState({
    customer_id: '',
    product_name: '',
    quantity: '',
    unit: 'MT',
    expected_dispatch_date: '',
    expected_delivery_date: '',
    notes: ''
  })
  const [existingProducts, setExistingProducts] = useState([{ ...EMPTY_PRODUCT }])

  const [newBuyerForm, setNewBuyerForm] = useState({
    // Customer Info
    company_name: '',
    contact_person: '',
    email: '',
    phone: '',
    country: '',
    address: '',
    customer_notes: '',
    // Order Info
    product_name: '',
    quantity: '',
    unit: 'MT',
    expected_dispatch_date: '',
    expected_delivery_date: '',
    notes: ''
  })
  const [newProducts, setNewProducts] = useState([{ ...EMPTY_PRODUCT }])

  // Load customers for selection when in existing mode
  useEffect(() => {
    if (workflowMode === 'existing') {
      const fetchCustomers = async () => {
        setLoadingCustomers(true)
        try {
          const res = await customersApi.list()
          setCustomers(res.data?.data || [])
        } catch (err) {
          console.error(err)
          toast.error('Failed to load customers list')
        } finally {
          setLoadingCustomers(false)
        }
      }
      fetchCustomers()
    }
  }, [workflowMode])

  // Handle click outside searchable customer dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Input change handlers
  const handleExistingChange = (e) => {
    const { name, value } = e.target
    setExistingBuyerForm(prev => ({ ...prev, [name]: value }))
  }

  const handleNewChange = (e) => {
    const { name, value } = e.target
    setNewBuyerForm(prev => ({ ...prev, [name]: value }))
  }

  // Clear selected customer
  const handleClearCustomer = () => {
    setExistingBuyerForm(prev => ({ ...prev, customer_id: '' }))
    setSearchTerm('')
  }

  // Dynamic product row handlers
  const handleProductChange = (setter, index, field, value) => {
    setter(prev => prev.map((p, i) => i === index ? { ...p, [field]: value } : p))
  }

  const handleAddProduct = (setter) => {
    setter(prev => [...prev, { ...EMPTY_PRODUCT }])
  }

  const handleRemoveProduct = (setter, index) => {
    setter(prev => prev.length > 1 ? prev.filter((_, i) => i !== index) : prev)
  }

  const productsToPayload = (products) =>
    products
      .filter(p => p.product_name.trim())
      .map(p => ({
        product_name: p.product_name.trim(),
        quantity: p.quantity ? Number(p.quantity) : null,
        unit: p.unit || null,
        notes: p.notes?.trim() || null,
      }))

  // Submissions
  const handleExistingSubmit = async (e) => {
    e.preventDefault()
    if (!existingBuyerForm.customer_id) {
      toast.error('Please select a customer')
      return
    }

    // Front-end date validation
    if (
      existingBuyerForm.expected_dispatch_date &&
      existingBuyerForm.expected_delivery_date &&
      existingBuyerForm.expected_delivery_date < existingBuyerForm.expected_dispatch_date
    ) {
      toast.error('Expected delivery date cannot be earlier than expected dispatch date')
      return
    }

    setLoading(true)
    try {
      const productList = productsToPayload(existingProducts)
      const payload = {
        customer_id: Number(existingBuyerForm.customer_id),
        product_name: existingBuyerForm.product_name || (productList[0]?.product_name || ''),
        quantity: existingBuyerForm.quantity ? Number(existingBuyerForm.quantity) : null,
        unit: existingBuyerForm.unit,
        expected_dispatch_date: existingBuyerForm.expected_dispatch_date || null,
        expected_delivery_date: existingBuyerForm.expected_delivery_date || null,
        notes: existingBuyerForm.notes || null,
        products: productList,
      }
      await ordersApi.create(payload)
      toast.success('Order created successfully')
      navigate('/orders')
    } catch (err) {
      console.error(err)
      // client.js interceptor handles standard error toasts, but we can capture special conditions here if needed
    } finally {
      setLoading(false)
    }
  }

  const handleNewSubmit = async (e) => {
    e.preventDefault()

    // Validate phone number format strictly
    const phoneRegex = /^\+?[\d\s\-()]+$/
    if (!phoneRegex.test(newBuyerForm.phone.strip ? newBuyerForm.phone.strip() : newBuyerForm.phone)) {
      toast.error('Phone number can only contain digits, spaces, dashes, parentheses, or +')
      return
    }

    // Date validation
    if (
      newBuyerForm.expected_dispatch_date &&
      newBuyerForm.expected_delivery_date &&
      newBuyerForm.expected_delivery_date < newBuyerForm.expected_dispatch_date
    ) {
      toast.error('Expected delivery date cannot be earlier than expected dispatch date')
      return
    }

    setLoading(true)
    try {
      const productList = productsToPayload(newProducts)
      const payload = {
        customer: {
          company_name: newBuyerForm.company_name,
          contact_person: newBuyerForm.contact_person || null,
          email: newBuyerForm.email,
          phone: newBuyerForm.phone,
          country: newBuyerForm.country || null,
          address: newBuyerForm.address || null,
          notes: newBuyerForm.customer_notes || null
        },
        order: {
          product_name: newBuyerForm.product_name || (productList[0]?.product_name || ''),
          quantity: newBuyerForm.quantity ? Number(newBuyerForm.quantity) : null,
          unit: newBuyerForm.unit,
          expected_dispatch_date: newBuyerForm.expected_dispatch_date || null,
          expected_delivery_date: newBuyerForm.expected_delivery_date || null,
          notes: newBuyerForm.notes || null,
          products: productList,
        }
      }
      await ordersApi.createWithNewCustomer(payload)
      toast.success('Customer onboarded & first order created successfully!')
      navigate('/orders')
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Filter customers based on search text input
  const filteredCustomers = customers.filter(c =>
    c.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (c.contact_person && c.contact_person.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const selectedCustomer = customers.find(c => c.id === Number(existingBuyerForm.customer_id))

  // Render Step 1 (Choice Screen)
  if (workflowMode === null) {
    return (
      <div className="max-w-2xl mx-auto space-y-6 py-6">
        <div>
          <h1 className="font-heading font-bold text-2xl text-slate-900">Create New Order</h1>
          <p className="text-sm text-slate-500 font-body mt-1">Select the starting point for this order creation workflow.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Option A: Existing Buyer */}
          <button
            onClick={() => setWorkflowMode('existing')}
            className="flex flex-col text-left p-6 bg-white border border-agri-200 hover:border-forest-500 hover:shadow-md rounded-xl transition-all group space-y-4 outline-none"
          >
            <div className="w-12 h-12 rounded-lg bg-forest-50 flex items-center justify-center text-forest-600 group-hover:bg-forest-100 transition-colors">
              <Users size={24} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 font-heading">Use Existing Buyer</h2>
              <p className="text-xs text-slate-500 font-body mt-1.5 leading-relaxed">
                Create an order for an established customer already stored in the system database.
              </p>
            </div>
          </button>

          {/* Option B: New Buyer */}
          <button
            onClick={() => setWorkflowMode('new')}
            className="flex flex-col text-left p-6 bg-white border border-agri-200 hover:border-forest-500 hover:shadow-md rounded-xl transition-all group space-y-4 outline-none"
          >
            <div className="w-12 h-12 rounded-lg bg-forest-50 flex items-center justify-center text-forest-600 group-hover:bg-forest-100 transition-colors">
              <UserPlus size={24} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 font-heading">Create New Buyer</h2>
              <p className="text-xs text-slate-500 font-body mt-1.5 leading-relaxed">
                Onboard a brand new customer company and initialize their login and first order.
              </p>
            </div>
          </button>
        </div>

        <div className="flex items-center justify-end pt-4 border-t border-agri-100">
          <Button variant="ghost" onClick={() => navigate('/orders')}>
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  // Render Step 2A (Existing Buyer Form)
  if (workflowMode === 'existing') {
    return (
      <div className="max-w-2xl mx-auto space-y-6 py-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setWorkflowMode(null)
              handleClearCustomer()
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-agri-200 text-slate-500 transition-colors shrink-0"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="font-heading font-bold text-xl text-slate-900">Create Order — Existing Buyer</h1>
            <p className="text-sm text-slate-500 font-body">Select a customer and fill out order details.</p>
          </div>
        </div>

        <form onSubmit={handleExistingSubmit} className="bg-white rounded-xl border border-agri-200 shadow-card p-6 space-y-6">
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-800 font-heading border-b border-agri-100 pb-2">Customer Selection</h2>
            
            <div className="relative" ref={dropdownRef}>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Search & Select Customer *</label>
              
              {!existingBuyerForm.customer_id ? (
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Search size={16} />
                  </span>
                  <input
                    type="text"
                    placeholder="Type company name or contact person..."
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value)
                      setIsDropdownOpen(true)
                    }}
                    onFocus={() => setIsDropdownOpen(true)}
                    className="w-full pl-9 pr-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                  />
                  {isDropdownOpen && (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-agri-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {loadingCustomers ? (
                        <div className="p-3 text-center text-xs text-slate-400 font-body">Loading customers...</div>
                      ) : filteredCustomers.length === 0 ? (
                        <div className="p-3 text-center text-xs text-slate-400 font-body">No customers found</div>
                      ) : (
                        filteredCustomers.map(c => (
                          <button
                            key={c.id}
                            type="button"
                            onClick={() => {
                              setExistingBuyerForm(prev => ({ ...prev, customer_id: String(c.id) }))
                              setSearchTerm(c.company_name)
                              setIsDropdownOpen(false)
                            }}
                            className="w-full text-left px-4 py-2 hover:bg-agri-50 text-sm text-slate-900 border-b border-agri-100 last:border-none font-body flex justify-between items-center"
                          >
                            <div>
                              <span className="font-semibold block">{c.company_name}</span>
                              <span className="text-xs text-slate-500">{c.contact_person || 'No contact person'} • {c.country || 'No country'}</span>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-between p-3.5 bg-agri-50 border border-agri-200 rounded-lg">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-900 font-heading">{selectedCustomer?.company_name}</span>
                      <span className="px-2 py-0.5 text-[10px] font-semibold bg-forest-100 text-forest-800 rounded-full">Selected</span>
                    </div>
                    <p className="text-xs text-slate-500 font-body">
                      {selectedCustomer?.contact_person && `Contact: ${selectedCustomer.contact_person} • `}
                      {selectedCustomer?.email && `${selectedCustomer.email} • `}
                      {selectedCustomer?.country}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleClearCustomer}
                    className="p-1.5 hover:bg-agri-200 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
                    title="Change Customer"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-800 font-heading border-b border-agri-100 pb-2">Order Details</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Commodity / Product Name</label>
                <input
                  type="text"
                  name="product_name"
                  value={existingBuyerForm.product_name}
                  onChange={handleExistingChange}
                  placeholder="e.g. Mixed spices (or add products below)"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              {/* Multi-product rows */}
              <div className="md:col-span-2 border-t border-agri-100 pt-4">
                <label className="block text-xs font-medium text-slate-700 mb-2">Products (optional — add multiple for multi-product orders)</label>
                {existingProducts.map((product, index) => (
                  <div key={index} className="flex items-start gap-2 mb-2 p-3 bg-agri-50 rounded-lg border border-agri-200">
                    <div className="flex-1 grid grid-cols-4 gap-2">
                      <div className="col-span-2">
                        <input
                          type="text"
                          value={product.product_name}
                          onChange={(e) => handleProductChange(setExistingProducts, index, 'product_name', e.target.value)}
                          placeholder="Product name"
                          className="w-full px-2.5 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        />
                      </div>
                      <div>
                        <input
                          type="number"
                          value={product.quantity}
                          onChange={(e) => handleProductChange(setExistingProducts, index, 'quantity', e.target.value)}
                          min="0.01"
                          step="0.01"
                          placeholder="Qty"
                          className="w-full px-2.5 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        />
                      </div>
                      <div className="flex gap-1">
                        <select
                          value={product.unit}
                          onChange={(e) => handleProductChange(setExistingProducts, index, 'unit', e.target.value)}
                          className="flex-1 px-2 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        >
                          <option value="MT">MT</option>
                          <option value="kg">kg</option>
                          <option value="bags">bags</option>
                          <option value="containers">containers</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => handleRemoveProduct(setExistingProducts, index)}
                          className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                          title="Remove product"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => handleAddProduct(setExistingProducts)}
                  className="flex items-center gap-1.5 text-xs text-forest-700 hover:text-forest-800 font-medium transition-colors"
                >
                  <Plus size={14} /> Add Product
                </button>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Quantity</label>
                <input
                  type="number"
                  name="quantity"
                  value={existingBuyerForm.quantity}
                  onChange={handleExistingChange}
                  min="0.01"
                  step="0.01"
                  placeholder="e.g. 500"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Unit</label>
                <select
                  name="unit"
                  value={existingBuyerForm.unit}
                  onChange={handleExistingChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                >
                  <option value="MT">MT (Metric Tons)</option>
                  <option value="kg">kg (Kilograms)</option>
                  <option value="bags">bags</option>
                  <option value="containers">containers</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Expected Dispatch Date</label>
                <input
                  type="date"
                  name="expected_dispatch_date"
                  value={existingBuyerForm.expected_dispatch_date}
                  onChange={handleExistingChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Expected Delivery Date</label>
                <input
                  type="date"
                  name="expected_delivery_date"
                  value={existingBuyerForm.expected_delivery_date}
                  onChange={handleExistingChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Order Notes</label>
                <textarea
                  name="notes"
                  value={existingBuyerForm.notes}
                  onChange={handleExistingChange}
                  rows={3}
                  placeholder="Any specific delivery instructions, requirements, or logistics details..."
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>
            </div>
          </div>

          {/* Alert */}
          <div className="bg-forest-50 border border-forest-100 rounded-lg p-3">
            <p className="text-xs text-forest-800 font-body">
              <strong>Process Note:</strong> Creating this order will automatically initialize the 9-stage tracking pipeline milestones and trigger notifications.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-agri-100">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setWorkflowMode(null)
                handleClearCustomer()
              }}
            >
              Back
            </Button>
            <Button type="submit" icon={Save} loading={loading}>
              Create Order
            </Button>
          </div>
        </form>
      </div>
    )
  }

  // Render Step 2B (New Buyer Onboarding + Order Form)
  if (workflowMode === 'new') {
    return (
      <div className="max-w-2xl mx-auto space-y-6 py-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setWorkflowMode(null)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-agri-200 text-slate-500 transition-colors shrink-0"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="font-heading font-bold text-xl text-slate-900">Create Order — New Buyer Onboarding</h1>
            <p className="text-sm text-slate-500 font-body">Onboard a new buyer company and create their first order profile.</p>
          </div>
        </div>

        <form onSubmit={handleNewSubmit} className="bg-white rounded-xl border border-agri-200 shadow-card p-6 space-y-6">
          {/* Section 1: Customer Info */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-800 font-heading border-b border-agri-100 pb-2">1. Customer / Buyer Profile</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Company Name *</label>
                <input
                  type="text"
                  name="company_name"
                  value={newBuyerForm.company_name}
                  onChange={handleNewChange}
                  required
                  placeholder="e.g. Acme Spices LLC"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Contact Person Name</label>
                <input
                  type="text"
                  name="contact_person"
                  value={newBuyerForm.contact_person}
                  onChange={handleNewChange}
                  placeholder="e.g. John Doe"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Email Address * (For Portal Access)</label>
                <input
                  type="email"
                  name="email"
                  value={newBuyerForm.email}
                  onChange={handleNewChange}
                  required
                  placeholder="e.g. john@acme.com"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Phone Number *</label>
                <input
                  type="text"
                  name="phone"
                  value={newBuyerForm.phone}
                  onChange={handleNewChange}
                  required
                  placeholder="e.g. +1 555-0199"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Country / Destination</label>
                <input
                  type="text"
                  name="country"
                  value={newBuyerForm.country}
                  onChange={handleNewChange}
                  placeholder="e.g. Germany"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Address (Optional)</label>
                <input
                  type="text"
                  name="address"
                  value={newBuyerForm.address}
                  onChange={handleNewChange}
                  placeholder="e.g. 123 Spice Way, Industrial Zone"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Customer Notes (Internal / Optional)</label>
                <textarea
                  name="customer_notes"
                  value={newBuyerForm.customer_notes}
                  onChange={handleNewChange}
                  rows={2}
                  placeholder="Important details about this buyer (e.g. preferred shipping lines, billing cycles)..."
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Order Info */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-800 font-heading border-b border-agri-100 pb-2">2. First Order Specifications</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Commodity / Product Name</label>
                <input
                  type="text"
                  name="product_name"
                  value={newBuyerForm.product_name}
                  onChange={handleNewChange}
                  placeholder="e.g. Mixed spices (or add products below)"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              {/* Multi-product rows */}
              <div className="md:col-span-2 border-t border-agri-100 pt-4">
                <label className="block text-xs font-medium text-slate-700 mb-2">Products (optional — add multiple for multi-product orders)</label>
                {newProducts.map((product, index) => (
                  <div key={index} className="flex items-start gap-2 mb-2 p-3 bg-agri-50 rounded-lg border border-agri-200">
                    <div className="flex-1 grid grid-cols-4 gap-2">
                      <div className="col-span-2">
                        <input
                          type="text"
                          value={product.product_name}
                          onChange={(e) => handleProductChange(setNewProducts, index, 'product_name', e.target.value)}
                          placeholder="Product name"
                          className="w-full px-2.5 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        />
                      </div>
                      <div>
                        <input
                          type="number"
                          value={product.quantity}
                          onChange={(e) => handleProductChange(setNewProducts, index, 'quantity', e.target.value)}
                          min="0.01"
                          step="0.01"
                          placeholder="Qty"
                          className="w-full px-2.5 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        />
                      </div>
                      <div className="flex gap-1">
                        <select
                          value={product.unit}
                          onChange={(e) => handleProductChange(setNewProducts, index, 'unit', e.target.value)}
                          className="flex-1 px-2 py-2 bg-white border border-agri-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-forest-500 font-body"
                        >
                          <option value="MT">MT</option>
                          <option value="kg">kg</option>
                          <option value="bags">bags</option>
                          <option value="containers">containers</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => handleRemoveProduct(setNewProducts, index)}
                          className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                          title="Remove product"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => handleAddProduct(setNewProducts)}
                  className="flex items-center gap-1.5 text-xs text-forest-700 hover:text-forest-800 font-medium transition-colors"
                >
                  <Plus size={14} /> Add Product
                </button>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Quantity</label>
                <input
                  type="number"
                  name="quantity"
                  value={newBuyerForm.quantity}
                  onChange={handleNewChange}
                  min="0.01"
                  step="0.01"
                  placeholder="e.g. 500"
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Unit</label>
                <select
                  name="unit"
                  value={newBuyerForm.unit}
                  onChange={handleNewChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                >
                  <option value="MT">MT (Metric Tons)</option>
                  <option value="kg">kg (Kilograms)</option>
                  <option value="bags">bags</option>
                  <option value="containers">containers</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Expected Dispatch Date</label>
                <input
                  type="date"
                  name="expected_dispatch_date"
                  value={newBuyerForm.expected_dispatch_date}
                  onChange={handleNewChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Expected Delivery Date</label>
                <input
                  type="date"
                  name="expected_delivery_date"
                  value={newBuyerForm.expected_delivery_date}
                  onChange={handleNewChange}
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">Order Notes</label>
                <textarea
                  name="notes"
                  value={newBuyerForm.notes}
                  onChange={handleNewChange}
                  rows={3}
                  placeholder="Any logistics details, shipping lines or product specifications..."
                  className="w-full px-3 py-2.5 bg-white border border-agri-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 outline-none focus:ring-2 focus:ring-forest-500 font-body"
                />
              </div>
            </div>
          </div>

          {/* Process Notes */}
          <div className="bg-forest-50 border border-forest-100 rounded-lg p-4 space-y-2">
            <p className="text-xs text-forest-800 font-body">
              <strong>Onboarding Note:</strong> A CUSTOMER-role login account will be generated automatically for the buyer contact email with the secure default password <code>Welcome@1234</code>. They will receive an email invitation containing their credentials.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-agri-100">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setWorkflowMode(null)}
            >
              Back
            </Button>
            <Button type="submit" icon={Save} loading={loading}>
              Onboard & Create Order
            </Button>
          </div>
        </form>
      </div>
    )
  }
}
