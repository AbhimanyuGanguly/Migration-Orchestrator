const { generateId } = require('./index');

test('generates a valid uuid', () => {
    const id = generateId();
    expect(id).toBeDefined();
    expect(typeof id).toBe('string');
});
