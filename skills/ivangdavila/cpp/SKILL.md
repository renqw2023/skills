---
name: C++
description: Avoid common C++ mistakes — memory leaks, dangling references, undefined behavior, and ownership confusion.
metadata: {"clawdbot":{"emoji":"⚡","requires":{"bins":["g++"]},"os":["linux","darwin","win32"]}}
---

## Memory Ownership
- Raw `new` without `delete` leaks — use `std::unique_ptr` or `std::make_unique`
- `std::unique_ptr` for single ownership — can't copy, only move
- `std::shared_ptr` for shared ownership — overhead of reference counting
- `std::make_shared` more efficient — single allocation for object and control block
- Raw pointers for non-owning references only — never `delete` a borrowed pointer

## Dangling References
- Returning reference to local variable — undefined behavior, object destroyed
- Reference to temporary extends lifetime only for const ref — not for ref to ref
- Capturing local by reference in lambda that outlives scope — use `[=]` or copy
- Iterator invalidation: `push_back` may relocate vector — don't hold iterators across modifications
- `string_view` doesn't own data — underlying string must outlive the view

## Undefined Behavior
- Array out of bounds — no runtime check, silent corruption
- Null pointer dereference — crash or worse, silent corruption
- Signed integer overflow — undefined, not wrap-around
- Use after free — memory may be reused, unpredictable behavior
- Data race on non-atomic — use `std::mutex` or `std::atomic`

## Rule of 0/3/5
- Rule of 0: no manual resource management — rely on smart pointers and RAII
- Rule of 3: if custom destructor, copy constructor, or copy assignment — define all three
- Rule of 5: add move constructor and move assignment — for efficient transfers
- `= default` to use compiler-generated — `= delete` to forbid operation

## Move Semantics
- `std::move` doesn't move — casts to rvalue reference, enables move
- Moved-from object in valid but unspecified state — don't use without reassigning
- Return local by value — compiler applies RVO/NRVO, don't std::move return values
- `&&` in parameter is rvalue reference — `&&` in type deduction is forwarding reference

## Initialization
- Braced init `{}` prevents narrowing — `int x{3.5}` is error, `int x(3.5)` truncates silently
- Most vexing parse: `Widget w();` declares function — use `Widget w{};` or `Widget w;`
- Member initializer list order follows declaration order — not list order, can cause bugs
- `static` locals initialized once — thread-safe since C++11

## const Correctness
- `const` method can be called on const object — mark methods that don't modify state
- `const` reference parameter avoids copy — use for read-only access
- `const_cast` to remove const is usually wrong — modifying originally const is UB
- `mutable` for members modified in const methods — caches, mutexes

## Virtual and Inheritance
- Base class needs virtual destructor — otherwise derived destructor not called through base pointer
- Object slicing: copying derived to base loses derived data — use pointers or references
- `override` keyword catches signature mismatches — always use when overriding
- `final` prevents further override — also enables devirtualization optimization

## STL Gotchas
- `vector<bool>` is not a container of bools — returns proxy, avoid or use `deque<bool>`
- `map[key]` inserts default if missing — use `find()` or `contains()` (C++20) to check
- `erase()` returns next iterator — use returned value in loop: `it = container.erase(it)`
- Range-for with modification — doesn't work, use index or iterator loop

## Modern C++ Patterns
- `auto` for complex types — but explicit for clarity when type matters
- Structured bindings: `auto [a, b] = pair;` — cleaner than `.first`, `.second`
- `std::optional` for maybe-values — better than pointer or sentinel
- `constexpr` for compile-time computation — catches errors earlier
- `[[nodiscard]]` on functions whose return shouldn't be ignored — warns on discard
